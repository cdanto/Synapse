#!/bin/zsh
URLS=(${LLAMA_URLS//,/ })
ok=1
for u in $URLS; do
  curl -s --max-time 2 "$u" >/dev/null && ok=0 && break
done
if [ $ok -ne 0 ]; then
  echo "$(date -Is) server down" >> workdir/logs/watchdog.log
  launchctl kickstart -k gui/$(id -u)/local.llama.primary
fi