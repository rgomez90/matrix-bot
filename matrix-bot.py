import simplematrixbotlib as botlib
from nio import (crypto, RoomEncryptedMedia)
import aiofiles
import aiofiles.os
import os
from urllib.parse import quote, urlparse
import json
import subprocess
import magic


def choose_available_filename(filename):
    if os.path.exists(filename):
        try:
            start, ext = filename.rsplit(".", 1)
        except ValueError:
            start, ext = (filename, "")
        i = 0
        while os.path.exists(f"{start}_{i}.{ext}"):
            i += 1
        return f"{start}_{i}.{ext}"
    else:
        return filename

### PROGRAMM ###
# Read Config JSON
with open('config.json') as json_file:
    appConfig = json.load(json_file)

# Create bot config
config = botlib.Config()
config.encryption_enabled = True
config.emoji_verify = False
config.ignore_unverified_devices = True
config.store_path = './crypto_store/'

# Create bot credentials
creds = botlib.Creds(appConfig['matrix']['homeserver_url'],
                     appConfig['matrix']['user'], appConfig['matrix']['password'])

# Create bot
bot = botlib.Bot(creds, config)

PREFIX = appConfig['command_prefix']  # Constant for bot's message prefix

async def download_and_decrypt_media(room, event, target_folder: str) -> str:
    media_mxc = event.url
    mxc = urlparse(media_mxc)
    response = await bot.async_client.download(mxc.netloc, mxc.path.strip("/"))
    data = response.body
    filename = os.path.join(target_folder, event.body)
    async with aiofiles.open(filename, "wb") as f:
        await f.write(
            crypto.attachments.decrypt_attachment(
                data,
                event.source["content"]["file"]["key"]["k"],
                event.source["content"]["file"]["hashes"][
                    "sha256"
                ],
                event.source["content"]["file"]["iv"],
            )
        )
        # Set atime and mtime of file to event timestamp
        os.utime(
            filename,
            ns=((event.server_timestamp * 1000000,) * 2),
        )
    return filename

def should_handle_event(room, event):
    if event.sender == bot.creds.username:
        return False
    w_rooms = appConfig["whitelist_rooms"]
    b_rooms = appConfig["blacklist_rooms"]
    if (len(w_rooms) > 0):
        return True if room.room_id in w_rooms else False
    if (len(b_rooms) > 0):
        return False if room.room_id in w_rooms else True
    return True

def update_verified_devices(room):
    roomUsers = bot.async_client.room_devices(room.room_id)
    for roomUser in roomUsers.items():
        for roomDevice in roomUser[1].items():
            olmDevice = roomDevice[1]
            if not olmDevice.verified:
                bot.async_client.verify_device(olmDevice)

# Listener will trigger on all message events (uncomment lines below  and complete function to activate)
# @bot.listener.on_message_event
# async def onNewEncryptedFile(room, event):
#     print(room)


# Listener will trigger when a file (not image, video, audio) is uploaded
@bot.listener.on_custom_event(RoomEncryptedMedia)
async def onNewEncryptedFile(room, event):
    # Ignore events where bot is the source or from channels that are blacklisted
    if not should_handle_event(room,event):
        return
    # Update whitelist with all devices in the room
    update_verified_devices(room)
    # Download and decrypt file. Response will be the relative path to the decrypted file
    s_filepath = await download_and_decrypt_media(room, event, appConfig['download_folder'])
    s_path_without_extension, file_extension = os.path.splitext(s_filepath)

    # If file is not quarto exit
    if file_extension != '.qmd':
        return

    # Send `working on it` message to let the user know quickly, that the bot has listened
    content = {
        "body": "Eine Quantor Datei! 🤓\n\nLass mich kurz daraus eine PDF Datei machen...⚙⚙\nIch hoffe alle zugehörige Dateien wurden bereits geladen!",
        "msgtype": "m.text",
        "format": "org.matrix.custom.html",
        "m.relates_to": {
            "m.in_reply_to": {
                "event_id": event.event_id
            }
        }
    }
    await bot.async_client.room_send(room.room_id, message_type="m.room.message", content=content)

    # Run cmd command to convert quarto to PDF
    cwd = os.path.join(os.getcwd(), appConfig['download_folder'])
    process = subprocess.run(
        ['quarto', 'render', event.body], cwd=cwd, capture_output=True, text=True)

    # Reaction result. Will only be used if reaction was enabled
    reaction = "💚 Konversion erfolgreich ✅" if appConfig["reaction"][
        "ok_msg"] is None else appConfig["reaction"]["ok_msg"]

    # If there is some error, set reaction and post message with stderr
    if process.returncode != 0:
        msg = f'Das hat leider nicht geklappt...😞\n\n Die PDF-Datei für {event.body} konnte nicht erstellt werden \n\n'
        msg += "## STDERR ##\n\n"
        msg += process.stderr
        reaction = "❌ Koversionsfehler ❌" if appConfig["reaction"][
            "error_msg"] is None else appConfig["reaction"]["error_msg"]
        await bot.api.send_text_message(room.room_id, msg)
    # If conversion was successful, upload file and post message with file link
    else:
        # Upload file to file repository
        o_filename = s_path_without_extension + ".pdf"
        mime_type = magic.from_file(o_filename, mime=True)
        file_stat = await aiofiles.os.stat(o_filename)
        async with aiofiles.open(o_filename, "r+b") as f:
            resp, decryption_keys = await bot.async_client.upload(
                f,
                content_type=mime_type,  # application/pdf
                filename=os.path.basename(o_filename),
                filesize=file_stat.st_size,
                encrypt=True,
            )

        # Send conversion completed message
        content = {
            "body": "✅ PDF erfolgreich erstellt! 🥳\n\n Laden Sie die Datei unten herunter 👇",
            "msgtype": "m.text",
            "format": "org.matrix.custom.html",
            "m.relates_to": {
                "m.in_reply_to": {
                    "event_id": event.event_id
                }
            }
        }
        await bot.async_client.room_send(room.room_id, "m.room.message", content)

        # Send file message
        content = {
            "body": os.path.basename(o_filename),
            "info": {"size": file_stat.st_size, "mimetype": mime_type},
            "msgtype": "m.file",
            "file": {
                "url": resp.content_uri,
                "key": decryption_keys["key"],
                "iv": decryption_keys["iv"],
                "hashes": decryption_keys["hashes"],
                "v": decryption_keys["v"],
            },
            "m.relates_to": {
                "m.in_reply_to": {
                    "event_id": event.event_id
                }
            }
        }
        resp = await bot.async_client.room_send(room.room_id, "m.room.message", content)

    # Send reaction to source file message (if enabled)
    if appConfig["reaction"]["enabled"]:
        content = {
            "m.relates_to": {
                "rel_type": "m.annotation",
                "event_id": event.event_id,
                "key": reaction,
            }
        }
        await bot.api.async_client.room_send(room.room_id, "m.reaction", content)

bot.run()
