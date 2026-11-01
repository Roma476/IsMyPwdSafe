# README assets

`demo.gif` is the terminal demo at the top of the project README. It is
generated from `demo.tape` with [VHS](https://github.com/charmbracelet/vhs).

## Regenerate

```bash
# Requirements:
#   - imps on PATH
#   - Node.js 18+ for --engine=ts
#   - network access for the live HIBP check
#   - vhs, ttyd, and ffmpeg
vhs docs/assets/demo.tape
```

The tape uses a public demo password, not a real secret. Keep the GIF small
enough to load quickly on GitHub and PyPI; the current asset is well under 1 MB.
