#!/bin/zsh
# Two Archeion instances from the PyPI wheel (sasana 2.0.2): A = the legitimate sealer, B = an attacker's own.
# Each: loopback only, throwaway key file in its own directory, HOME redirected so ~/.archeion is never read or written.
S=/private/tmp/claude-501/-Users-lulu-Desktop-Sasana/ac33ea6b-027e-4591-8d50-fc1919ab0095/scratchpad
for pair in A:18747 B:18748; do
  name=${pair%%:*}; port=${pair##*:}
  d=$S/work/archeion_$name; mkdir -p $d/home
  ( cd $d && HOME=$d/home ARCHEION_KEY_FILE=$d/server_key.b64 SASANA_TSA_URL=http://127.0.0.1:9/ \
      exec $S/venv/bin/uvicorn archeion.server:app --host 127.0.0.1 --port $port --log-level warning ) &
done
wait
