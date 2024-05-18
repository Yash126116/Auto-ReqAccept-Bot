from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid, BadRequest
from pyrogram import Client, filters
from pyrogram.types import *
from motor.motor_asyncio import AsyncIOMotorClient  
import os
import asyncio, datetime, time

ACCEPTED_TEXT = "Hey {user}\n\nYour Request For {chat} Is Accepted ✅"
START_TEXT = "Hai {}\n\nI am Auto Request Accept Bot Working For All Channels. Add Me In Your Channel and Forward a Message From That Channel"
SUCCESS_MESSAGE = "Success! The bot has the required permissions."
FAILED_MESSAGE = "Failed to add. The bot does not have 'invite_users' permission. Please add the required permission using the button below."

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_URL = os.getenv('DB_URL')
ADMINS = [int(os.getenv('ADMINS'))] if os.getenv('ADMINS') else []

# Debugging Information
print("Environment Variables:")
print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH}")
print(f"BOT_TOKEN: {BOT_TOKEN}")
print(f"DB_URL: {DB_URL}")
print(f"ADMINS: {ADMINS}")

Dbclient = AsyncIOMotorClient(DB_URL)
Cluster = Dbclient['Cluster0']
Data = Cluster['users']
Bot = Client(name='AutoAcceptBot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@Bot.on_message(filters.command("start") & filters.private)
async def start_handler(c, m):
    user_id = m.from_user.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
    button = [[
        InlineKeyboardButton('Updates', url='https://t.me/mkn_bots_updates'),
        InlineKeyboardButton('Add Me', url='https://t.me/Request_Admin_Approvalbot?startchannel=log&admin=post_messages+edit_messages+delete_messages+invite_users+add_admins+change_info')
    ]]
    return await m.reply_text(text=START_TEXT.format(m.from_user.mention), disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(button))

@Bot.on_message(filters.command(["broadcast", "users"]) & filters.user(ADMINS))
async def broadcast(c, m):
    if m.text == "/users":
        total_users = await Data.count_documents({})
        return await m.reply(f"Total Users: {total_users}")
    b_msg = m.reply_to_message
    sts = await m.reply_text("Broadcasting your messages...")
    users = Data.find({})
    total_users = await Data.count_documents({})
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    async for user in users:
        user_id = int(user['id'])
        try:
            await b_msg.copy(chat_id=user_id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await b_msg.copy(chat_id=user_id)
            success += 1
        except InputUserDeactivated:
            await Data.delete_many({'id': user_id})
            failed += 1
        except UserIsBlocked:
            failed += 1
        except PeerIdInvalid:
            await Data.delete_many({'id': user_id})
            failed += 1
        except Exception as e:
            failed += 1
        done += 1
        if not done % 20:
            await sts.edit(f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}")
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.delete()
    await m.reply_text(f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}", quote=True)

@Bot.on_message(filters.forwarded & filters.private)
async def forwarded_handler(c, m):
    if m.forward_from_chat:
        chat_id = m.forward_from_chat.id
        chat_member = await c.get_chat_member(chat_id, 'me')
        if chat_member.can_invite_users:
            await m.reply_text(SUCCESS_MESSAGE)
        else:
            button = [[
                InlineKeyboardButton('Add Me', url='https://t.me/Request_Admin_Approvalbot?startchannel=log&admin=invite_users')
            ]]
            await m.reply_text(FAILED_MESSAGE, reply_markup=InlineKeyboardMarkup(button))

@Bot.on_chat_join_request()
async def req_accept(c, m):
    user_id = m.from_user.id
    chat_id = m.chat.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
    await c.approve_chat_join_request(chat_id, user_id)
    try:
        await c.send_message(user_id, ACCEPTED_TEXT.format(user=m.from_user.mention, chat=m.chat.title))
    except Exception as e:
        print(e)

# Attempt to synchronize time manually
async def main():
    while True:
        try:
            await Bot.start()
            print("Bot started successfully.")
            break
        except BadRequest as e:
            if str(e) == "[16] The msg_id is too low, the client time has to be synchronized.":
                print("Synchronizing time...")
                time.sleep(5)
            else:
                raise

loop = asyncio.get_event_loop()
loop.run_until_complete(main())