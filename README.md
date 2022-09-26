# Matrix-bot
This is a bot for matrix based in [matrix-nio](https://github.com/poljar/matrix-nio) and [simple-matrix-bot-lib](https://github.com/i10b/simplematrixbotlib).

The bot can be changed or extended with more functionality.

---

As for now the bot listens to new uploaded files and saves them to a predefined path.

If the uploaded file is a [quarto](https://quarto.org/) file with `.qmd` extension, a subprocess will be started to convert the file to PDF (via `quarto`) and post the output PDF back as a response to the message containing the source `qmd` file.

Optionally, the bot can react to the source message, letting the user(s) know, if the conversion was successful or not.

If in the process an exception is thrown, the stderr of the executed command, will be posted to the channel.

---

## Installing

The bot installation is an easy process, but there are a few things we have to do to make it run properly.

In order to convert quarto files a valid installation of quarto and dependencies is need.

### Bot Account

Normally the bot will work under its own account, so first create in Matrix an account for our bot and save the credentials for later use to sign-in.

### E2EE Support

For E2EE support, `python-olm` is needed, which requires the `libolm C library (version 3.x)`.

First make sure you have 'libolm' installed.

If not installed, we need to install it. On Debian and Ubuntu one can use `apt-get` to install package `libolm-dev`. On Fedora one can use `dnf` to install package `libolm-devel`. On MacOS one can use brew to install package libolm. Make sure version 3 is installed.

After checking `libolm` is successfully installed, we go on with the python dependencies.

### Python dependencies

For the python dependencies we will make use of virtual environments and the file [requirements.txt](requirements.txt)

To install the python dependencies, first create a virtual environment

```cmd
python3 -m venv venv
```

Activate it
```
`./venv/bin/activate`
```

Install dependencies
```
pip install -r requirements.txt
```

## Configuration
As configuration the bot uses `config.json` which can be edited to match requirements (at least `matrix` section will be edited).

The files will be saved in a predefined folder, which can be set via `config.json` in `download_folder`.

### Example config file

```json
{
  "command_prefix": "!c",
  "matrix": {
    "user": "bot",
    "user_id": "@bot:example.com",
    "password": "yourPassword",
    "homeserver_url": "https://example.com"
  },
  "quarto_command": "quarto render",
  "download_folder": "./downloads",
  "whitelist_rooms": [],
  "blacklist_rooms": [],
  "reaction": {
    "enabled": "True",
    "ok_msg": "💚 Converted! ✅",
    "error_msg": "❌ Error converting ❌"
  }
}
```

### Settings

| Setting | Description |
|---------|-------------|
| command-prefix | The prefix to use in messages which should be listened by the bot |
|matrix.user| Matrix bot's username |
|matrix.user_id| Matrix bot's userId (ex. @bot:example.com) |
|matrix.password| Matrix bot's account password|
|matrix.homeserver_url| Matrix Server URL|
|download_folder| relative path from root of downloads folder |
|blocklist_rooms| list of room-IDs to ignore for the bot |


## Running the bot

To run the bot, first install it (see [Installation](##Installing)) and then from the root folder run `matrix-bot`

### Session verification E2EE (needs an external element client web/browser)
In encrypted rooms in order to have access to encrypted messages and files, the bot's session has to be verified.
A file `session.text` and a folder `crypto_store` will be created at start of the bot if not present, which will create a new (untrusted) device (so verification should be done again)

To verify a device, first run the bot a first time with correct credentials.
After connecting the bot will response in the terminal with a `session-id` and a `fingerprint`

**Example response**
```
Connected to https://example.com as @bot:example.com (GQNCMMKORY)
This bot's public fingerprint ("Session key") for one-sided verification is: jD1m e6gr WGFw ZrW9 f4mJ NqEP uFL+ ARQv JENu Dkuz aiA
```
This will create an `unverified device` for the bot user, which should verified.

To verify this new device we login into a client (web/dekstop) using the bot's credentials.

Now, let's check the list of verified and unverified devices. For this, go to `channel information` - `Users`

![shot1](/docs/media/shot1.png)

click on the untrusted device (in this case `Bot Client using Simple-Matrix-Bot-Lib`) and click on `Manually verify by text`.

![shot2](/docs/media/shot2.png)

Now compare the session key from the bot terminal and the one from the client. Both should be the same. If so click in `Verify session`

After verification the bot should be able to decrypt messages and files sent in the joined channels, as well as encrypting messages and files sent from the bot to the channel.


