[< Back](README.md)

# Working on the project locally in a devcontainer

To work locally on the project in a devcontainer, do the following:

- If you use Windows:

  - For existing symlinks in the project to clone correctly, you need to have `git config core.symlinks=true` and the user must have `SeCreateSymbolicLinkPrivilege` permission:
    - Set `git config --global core.symlinks true` - this only needs to be done once globally, at the beginning.
    - Go to "Settings" (`Win + I`) > "System" > "Advanced" > "For developers" - this only needs to be done once globally, at the beginning.
  - In the cloned project under the `.devcontainer` folder, create a `.env` file containing `HOME=C:\Users\<my_user>`. This creates the `HOME` variable for the devcontainer environment as it exists on Linux and MacOS.

- Install [Docker Desktop](https://docs.docker.com/desktop/). **ATTENTION:** It is not enough to just install the downloaded installer! Read the following instructions carefully. **ATTENTION:** On ARM-based architectures (currently only MacOS), some versions of Docker have issues. In that case, you just need to google the error.

- Install [VS Code](https://code.visualstudio.com/download).

- In VS Code, install the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) and [Docker](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker) extensions.

- Open the project in VS Code. If you are in the console in the project folder, simply run `code .`. For a more comfortable reading of this guide in VS Code, press `CTRL SHIFT V`.

- Once in VS Code, press `CTRL SHIFT P` and select `Dev Containers: Rebuild Without Cache and Reopen in Container`. Wait for VS Code to switch into the devcontainer. If you see a VS Code warning saying `Cannot activate the 'XYZ' extension because it depends on the 'Python' extension, which is not loaded. ...`, just click `Reload Window`. This is just because some VS Code extensions require the `Python` extension to be installed, which might not have loaded due to timing, and `Reload Window` will fix it.

## Initial Odoo startup and database initialization

- Once in VS Code in the devcontainer, run the `odoo` command in the console.

- Open http://localhost:50000/ in your browser. This URL is also available in VS Code in the "Ports" tab (`CTRL P` > `view ports`) > "drinkcentrum-is-odoo odoo". Upon the first Odoo run, a configuration screen will appear to set the database name and Odoo access credentials:<br><img src="./img/odoo-create-db-screen.png" style="width:400px;"><br>Enter the same credentials (especially the database name) so the project works based on preconfigured values in [`.devcontainer/config/odoo.conf`](../.devcontainer/config/odoo.conf) and [`.devcontainer/docker-compose.yml`](../.devcontainer/docker-compose.yml). You can also select a specific language and country. The fiscal localization (taxes, etc.) will be configured according to the selected country. You can also check the box to load demo data.<br><br>NOTE: **To make Odoo database manager easily accesible** add following bookmarklet:<br>`javascript:(function(){var u=location.origin+'/web/database/manager';if(location.href===u){location.reload();}else{location.href=u;}})();`<br>Add it as a bookmark in your browser.

- After the initial database creation, the login screen will appear. If you entered the credentials above, you can log in using the username `test@run.sk` and password `odoo`.

- Search for the `my_module` module in the displayed list of applications and activate it. After activating the module, you will likely be redirected to the "Discuss" > "Inbox" screen. To access the installed `my_module` module, click the top left icon ![Home Menu](./img/odoo-home-menu.png) and select the desired module.

### Multiple databases

To create another Odoo database, use the following procedure:

- Once in VS Code in the devcontainer, run the `odoo` command in the console.
- Open the [database manager URL](http://localhost:50000/web/database/manager).
- Click "Create Database" and create a new database according to the guide above. Just change the "Database Name" to, e.g., `odoo_1`.

If the `odoo` command is started without explicitly specifying a database, you can switch databases when logging into Odoo.
If the `odoo` command is started with an explicit database specified (e.g., `odoo -d odoo_1`), you cannot switch databases at login.

Multiple databases can be used, for example, to keep one loaded with Odoo demo data and have a second clean database ready for production data upload. To run two concurrent Odoo instances with different databases, open the running Odoo application in two different browsers (or use an incognito window of the given browser) and select a different database in each.

### Database reset

If you messed up the database during testing and it would be best to start over, do the following:

- Open the [database manager URL](http://localhost:50000/web/database/manager).
- Click "Delete" and enter the "Master password" (it should be set to `odoo` if you created the DB according to the guide above).
- Recreate the database according to the guide above.

### Export and import database

This is described in the guide on [running the project in a production environment via Docker](prodcontainer-deployment.md).

## Database access

Three options are prepared in the devcontainer for working with the database:

- **PgAdmin** - in VS Code in the "Ports" tab (`CTRL P` > `view ports`), click the link "drinkcentrum-is-odoo pgadmin" (the port of this link changes because PgAdmin runs as a separate service - see `docker-compose.yml`). The credentials to log into PgAdmin are username `test@run.sk` and password `odoo` (see `docker-compose.yml` > `services` > `pgadmin` > `environment`). On first login, you need to connect the database:
  - Click "Add New Server":<br>![Add New Server](./img/pgadmin-add-new-server.png).
  - Fill in the DB connection details (password is `odoo`):<br><img src="./img/pgadmin-register-server-general.png" style="width:400px;"><br><br><img src="./img/pgadmin-register-server-connection.png" style="width:400px;">
- **SQLTools** extension in VS Code - click the "SQLTools" extension icon (![SQLTools](./img/vs-code-sqltools-icon.png)) in the left side menu, and under the available connection "Project DB", click the green plug icon on the right:<br>![Connect](./img/vs-code-sqltools-connections.png).
- **psql** - to run the console tool, either run the `psql -h db -d odoo -U odoo` command in the VS Code terminal (`CTRL SHIFT T`) and enter password `odoo`, or run `make db-cli` in the console, which is an alias/shortcut for the previous command (see `Makefile`). To quickly get acquainted with working in `psql`, see this [cheat sheet](https://quickref.me/postgres.html). To exit `psql`, type `\q`.

## Environment description

Odoo is installed in `/usr/lib/python3/dist-packages/odoo` and linked into the project folder as `odoo-sources` (symbolic link). Installed Odoo modules are located in the `odoo-sources/addons` folder. Core modules (`res`, `ir`) are located in the `odoo-sources/addons/base` folder.

The `odoo-bin` command is available in the devcontainer as `odoo`. [Description of available parameters](https://www.odoo.com/documentation/17.0/developer/reference/cli.html) for this command.

The configuration file is `.devcontainer/config/odoo.conf`.

New internal (custom written) modules are added to the `extra-addons` folder. New external (downloaded) modules are added to the `vendor-addons` folder.

### Installing Python packages

To install additional Python packages using `pip3`, you need to modify `.devcontainer/Dockerfile.dev-odoo17` as follows:

- Add the necessary packages in the `# Install following Python packages:` section.
- Rebuild the Docker image according to the instructions in `.devcontainer/Dockerfile.dev-odoo17` > `BUILD & RUN COMMANDS:`.
- In VS Code, press `CTRL SHIFT P` and select `Dev Containers: Rebuild Without Cache...`.

To effectively share the changes with others, you need to push the new Docker image to DockerHub according to the instructions in `.devcontainer/Dockerfile.dev-odoo17` > `PUBLISH ON DOCKERHUB:`.

## Everyday work

For daily work on the project, it is sufficient in VS Code to press `CTRL SHIFT P` and select `Dev Containers: Reopen in Container` to switch to the devcontainer. Wait for VS Code to switch to the devcontainer.

When working on `my_module` (in the `odoo` database), you can use the following commands:

- **Run Odoo** and update `my_module` with the latest changes: `odoo -d odoo -u my_module`
  - To update multiple modules at once, use `-u my_module_1,my_module_2`.
  - **Command output** is written to `/var/log/odoo/odoo.log`. This is configured in the `.devcontainer/config/odoo.conf` > `logfile` file. If this configuration were commented out, the output would print directly to the console. The `/var/log/odoo` folder is linked to the project folder as `tmp/log`. Another option to capture output to the `odoo.log` file directly in the project folder is to use `odoo -d odoo -u my_module > odoo.log 2>&1`.
  - If you want to use the **debugger**, run: `python3 -m debugpy --listen 0.0.0.0:5678 /usr/bin/odoo -d odoo -u my_module` and then press `SHIFT F5` (to stop the automatically started debug connection) and then press `F5` (to start the debug connection based on ['.vscode/launch.json`](../.vscode/launch.json)).
  - Optionally, you can also append the [`--dev` parameter](https://www.odoo.com/documentation/17.0/developer/reference/cli.html#cmdoption-odoo-bin-dev) to the `odoo` commands.
- To update the `my_module` module again, stop the running `odoo` command using `CTRL C` and run it again in the same way as above.

You don't need to type these commands every time, as the console command history is fully functional in the devcontainer.

If you want to view the logs of the running `odoo` process, click "Remote Explorer" (![Remote Explorer](./img/vs-code-remote-explorer-icon.png)) in the side menu, search for the project container in the "Dev Containers" list, right-click it, and select "Show Container Log" from the context menu.

### Running tests

Tests in `extra-addons/*/tests/` are native Odoo unit tests (`TransactionCase`). They can be run in two ways:

#### Method 1: `odoo --test-enable` (standard)

```bash
odoo -d odoo -u my_module --test-enable --stop-after-init --no-http
```

Test results are written to the log (to the `tmp/log/odoo.log` file in the project folder). To find them quickly, use the regex `(FAIL|ERROR|failed|error\(s\)|odoo\.tests\.result)`.

#### Method 2: `pytest-odoo` (more suitable for TDD)

`pytest-odoo` is installed in the devcontainer (via `requirements.txt`). It offers the following advantages over `--test-enable`:

- output directly in the console (colored, clear)
- filtering tests via `-k "test_name"` or `-m "marker"`
- the module is upgraded only once when needed, not on every test run

**Procedure:**

1. First **upgrade the module** (only when the module's code has changed):

   ```bash
   odoo -d odoo -u my_module --stop-after-init
   ```

2. Run **tests via pytest**:

   ```bash
   pytest --odoo-database=odoo --odoo-config=/etc/odoo/odoo.conf \
       extra-addons/my_module/tests/ -v
   ```

   Filtering examples:

   ```bash
   # Only one test file
   pytest --odoo-database=odoo --odoo-config=/etc/odoo/odoo.conf \
       extra-addons/my_module/tests/test_something.py -v

   # Only tests containing "avco" in the name
   pytest --odoo-database=odoo --odoo-config=/etc/odoo/odoo.conf \
       extra-addons/my_module/tests/ -k "avco" -v
   ```

> **Note:** `pytest-odoo` always runs tests as `post_install` — therefore, the module must be updated before running the tests.

### Connecting Ventor application

To connect the [Ventor PRO](https://ventor.app/) application to Odoo running on your laptop/computer, do the following:

- Your laptop/computer and mobile device must be connected to the same local network, i.e., most easily the same WiFi network.
- Find your laptop/computer's IP address in the network. For example, using the command (Linux) `hostname -I` in the console. It will be an address like `192.168.x.x`.
- In the Ventor mobile application, set the server address to `http://192.168.x.x:50000` (replace `x.x` with your laptop/computer's actual address, the port is the same as for accessing Odoo from the browser on your laptop/computer).
- If it does not work, check if the firewall is active on your laptop/computer:
  - Linux (e.g. Ubuntu): `sudo ufw status` and if it is, deactivate it using the command `sudo ufw disable`

Ventor PRO [quickstart Guide](https://ventor.app/guides/ventor-quick-start-guide/). For test barcodes see [here](https://docs.google.com/document/d/1647nlhyQHnsKr95KXTAPdBhIgkO9sh6XzhOr-GMUIaU/edit?usp=sharing).

### Searching

Since the Odoo source files are "only" linked to the project, VS Code does not search in them unless "files to include" are specified in the "SEARCH" panel. The following options are available for "files to include":

- `./*` - if you want to search **also in Odoo source files**
- `./*/**/*.py` - if you want to search **only in a specific file type** (this is an example for `.py` files)
- `./odoo-sources` - if you want to search **only in Odoo source files**
- `./odoo-sources/**/*.py` - if you want to search **only in Odoo source files** and **only in a specific file type** (this is an example for `.py` files)

If you want to exclude all files that are part of tests from the search (including Odoo source files), specify `./*/**/tests/` as "files to exclude".

To search for models that inherit (extend) a given model, use regex. For example, for the model `res.config.settings` it would be: `_inherits?\s*=\s*['"]res.config.settings['"]`.

### Git

Creating a new branch: `git switch -c new-branch`.

List of branches not yet merged into the `main` branch: `git branch -r --no-merged main`.
