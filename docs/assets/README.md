# README assets

`demo.gif` is the terminal demo at the top of the project README. It is
generated from `demo.tape` with [VHS](https://github.com/charmbracelet/vhs).

`social-preview.png` is the 1280x640 GitHub social preview. Regenerate it with:

```bash
python docs/assets/make-social-preview.py
```

The generator uses Pillow and the Lato/DejaVu fonts available on most Linux
systems. Upload the PNG under repository **Settings → General → Social preview**.

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
