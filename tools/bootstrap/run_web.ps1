Set-Location 'F:\codex project\code2'
& 'F:\codex project\code2\.venv\Scripts\python.exe' -u main.py 2>&1 | Tee-Object -FilePath 'F:\codex project\code2\tools\bootstrap\run_web.log'
