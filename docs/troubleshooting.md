# Troubleshooting

**`agy -p` says it ran nothing and lists `denied_actions`.**
That's expected in terminal mode: headless agy can't run commands. Claude runs the plan's blocks. Don't "fix" it with allow rules (see the security model in the README).

**Gemini reports "all tests pass".**
In terminal mode it couldn't have run them. Claude runs the RED/GREEN blocks; the report is not evidence.

**herdr shows the agent `idle`, but nothing happens.**
A permission dialog can be open while the status says idle. Look at the screen: `herdr agent read gemini-exec --source visible`.

**The watchdog stopped with `TRUNCATED:`.**
The command didn't fit on screen, so the watchdog can't check it. Read it in the pane; if it's legitimate, approve that one with `herdr agent send-keys gemini-exec enter` and restart the watchdog.

**The watchdog stopped with `FORBIDDEN:` on something harmless.**
False positives are by design (for example, a commit message or a file path that mentions `git push`, `migration` or `deploy`). Check it, approve that one by hand, and restart the watchdog.

**The watchdog vanished after 30 minutes.**
Monitor expires after 30 minutes and takes the watchdog with it. Restart it right away if Gemini is still working, and never run two at once.

**A Monitor pipeline delivers no events.**
`| sed | cut` without flushing buffers forever. Use `grep --line-buffered` or `sed -u`, and avoid `cut` at the end.

**`next_block.py` shows `last OK/FAILED: ['FAILED']`, but the step worked.**
That can be the `|| echo FAILED` text of the command itself, wrapped on screen. The real output of the step (`/tmp/<prefix>_*`) decides.

**A Bash call timed out waiting for CI or a deploy.**
Claude Code's Bash calls stop at 10 minutes. Run long waits in the background, or check the state directly.

**After a deploy the old container logs are gone.**
Deploys recreate containers. For history, query the database or your log store.

**You switched the executor model and things got worse.**
A new model can format tool arguments differently. Watch the first runs closely after any model change.
