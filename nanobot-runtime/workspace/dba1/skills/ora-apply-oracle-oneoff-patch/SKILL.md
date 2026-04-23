---
name: apply-oracle-oneoff-patch
description: Execute the Oracle one-off patch installation process on a Linux host. Invoke this when the user asks to “apply a one-off patch / run opatch apply / install a patch according to the README”.
---

# Apply Oracle One-off Patch

This Skill is used to execute the Oracle one-off patch installation process on a Linux host, including OPatch self-check/replacement, patch extraction, prerequisite checks, installation, and result verification.

## Coordination with Other Skills / Tools

- Reuse the `linux-inventory` Skill first for host connection and alias identification
- In a Windows environment, prefer using the `win_ssh_linux` tool to execute remote commands
- Only fall back to a generic command execution method when the above tools cannot complete the task

## Standard Execution Strategy

- Identify the host and connection parameters first, then perform the patch actions; do not skip steps
- Each stage must include: “executed command + raw output + conclusion”
- By default, treat `README.txt` as the highest priority; if it conflicts with the general process, follow the README
- Before any destructive action, a rollback backup must be created first

## When to Use

- The user requests installation of an Oracle one-off patch
- The user provides a Bug number or patch package name and asks to complete the patch installation, or tells you the patch location on the Linux host

## Input and Recognition Rules

- First connect to the target Linux host via SSH and switch to the `oracle` user context
- Read `/home/oracle/.bash_profile` to obtain and export database-related environment variables
- Default patch search directories: `/oracle/patch`, `/oracle/soft`, `/tmp/soft`, `/tmp/patch`; if these directories cannot be found, stop execution and ask the user to provide the patch directory
- Common patch package naming pattern: `p<patch_number>_<version>_<platform>.zip`
- The OPatch utility patch number is fixed as: `6880880`
- The user may provide only a Bug number; in that case, first locate a matching patch in the patch directory before proceeding
- Check the current patch level by running `$ORACLE_HOME/OPatch/opatch lsinventory` to view installed patches

## Connection Preparation

1. First call the `linux-inventory` Skill to complete host name / alias matching
2. Obtain the target host IP, default user, SSH key, and privilege escalation method
3. Under Windows, generate and use a reusable connection method
4. After connecting successfully, execute first:
   - `hostname`
   - `id`
   - `echo $ORACLE_HOME`
   - `source /home/oracle/.bash_profile && echo $ORACLE_HOME`
5. If `ORACLE_HOME` is empty, stop the installation and fix the environment variables first

## Execution Process

1. Confirm the patch and tool package
   - Confirm that the patch package requested by the user exists
   - Confirm whether the OPatch package `p6880880*.zip` exists
   - Output the list of candidate files and the final selected patch package name
   - If the customer asks you to upload the patch package, use the `win_ssh_linux` tool to upload it to the patch directory; if that directory does not exist, stop execution and ask the user to provide the directory

2. Prepare OPatch
   - If `p6880880*.zip` is found:
     - Back up the existing tool: `mv $ORACLE_HOME/OPatch $ORACLE_HOME/OPatch_back`
     - Extract the OPatch package into `$ORACLE_HOME`
   - Verify that OPatch is available: `$ORACLE_HOME/OPatch/opatch version`
   - If OPatch is not available, stop the subsequent steps and return an error

3. Extract the target patch and read the instructions
   - Extract `p<patch_number>_<version>_<platform>.zip` in the directory where the patch package is located
   - Enter the extracted directory (usually the patch number directory)
   - Read `README.txt` and execute according to the document requirements
   - Extract and output the key installation steps (database shutdown requirements, prerequisite checks, rollback information)

4. Standard installation actions (follow `README.txt`)
   - Shut down the database:
     - `sqlplus / as sysdba`
     - `shutdown abort`
   - Verify database processes: `ps -ef | grep smon`
   - Reload the environment:
     - `source /home/oracle/.bash_profile`
     - `export PATH=$PATH:/usr/ccs/bin`
   - After entering the patch directory, run the conflict check:
     - `opatch prereq CheckConflictAgainstOHWithDetail -ph ./`
   - Continue only when the output contains `CheckConflictAgainstOHWithDetail passed`

5. Execute patch installation
   - Use the following command to automatically answer the two confirmation prompts:
     - `(printf 'y\ny\n') | $ORACLE_HOME/OPatch/opatch apply`
   - The SSH execution timeout should be set to `300` seconds
   - If the installation fails, analyze the possible cause and try the installation again

6. Post-install verification and cleanup
   - Verify that the patch has been installed:
     - `$ORACLE_HOME/OPatch/opatch lsinventory | grep <patch_number>`
   - If the installation succeeds, delete the backup directory:
     - `rm -rf $ORACLE_HOME/OPatch_back`
   - If the installation fails, keep `$ORACLE_HOME/OPatch_back` for rollback

7. After successful installation, start the database
   - Ask the user whether they want you to start the database
   - If the user confirms, execute the following commands to start the database:
     - `sqlplus / as sysdba`
     - `startup`

8. Install datapatch
   - If `README.txt` contains datapatch installation steps, execute datapatch according to the steps in `README.txt`
   - Note: datapatch execution may take a relatively long time; a timeout of 600 seconds is recommended
     
## Security and Idempotency Requirements

- Do not execute `mv` or `rm -rf` before confirming `ORACLE_HOME`
- Before deletion, you must double-check that the target path is neither empty nor the root path
- If the same patch number already exists in `lsinventory`, do not reinstall it by default; instead, return “already installed”
- Silent error swallowing is prohibited throughout the process; the raw error output must be preserved

## Output Requirements

- Clearly output the result of each step: success / failure / skipped
- If failed, provide the failed step, error message, and next-step recommendation
- The final output must include:
  - The actual installed patch number
  - The `lsinventory` verification result
  - Whether cleanup was completed
  - Which Skills / Tools were used (such as `linux-inventory`, `win_ssh_linux`)