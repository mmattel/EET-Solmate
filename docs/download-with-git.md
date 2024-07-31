# Download and Update esham Using git

Using git is handy as it takes care for any changes in the source automatically.

Depending on your environment, git may already be installed like when using Linux or needs to be installed
like when using Windows. To install git, follow the guide in
[Getting Started - Installing Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

For ease of handling, clone this repo locally using [git clone](https://github.com/git-guides/git-clone).
As rule of thumb, use your home directory as target. **Note** that the directory `solmate` will be created
*in the directory you are issuing the command*!

* **Change into your homedirectory**
  ```
  cd ~
  ```
* **Initial Cloning**

  * **Use the following commands if you have not cloned esham before**:  
    ```
    git clone --depth 1 https://github.com/mmattel/eet-solmate.git solmate
    git fetch --all --tags
    ```
* **Use the following commands for updates**
  * Note that this will drop any changes you have made
    **except for the .env configuration file**.  
    ```
    cd ~/solmate
    git checkout main
    git stash -u && git stash drop
    git pull --rebase origin main
    git fetch --all --tags
    ```
* **Switch to the solmate version you want to use**\
  The example uses v7.0.0
  ```
  git tag -l
  git checkout tags/v7.0.0
  ```

You now have cloned/updated `esham` and switched to the required version.