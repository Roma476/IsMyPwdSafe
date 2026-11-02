# Regenerate from the repository root with:
#   vhs docs/assets/demo.tape
#
# Requires `imps` on PATH, Node.js 18+ (for --engine=ts), and network access for
# the live HIBP check in the first scene. The password is a public demo value.

Output docs/assets/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 900
Set Padding 24
Set Theme "Dracula"
Set TypingSpeed 45ms
Set CursorBlink false

Type 'imps --engine=ts "password123"'
Enter
Sleep 6s

Type 'echo "exit=$?"'
Enter
Sleep 4s

Ctrl+L
Sleep 500ms

Type 'imps --engine=ts --offline "correct-horse-battery-staple"'
Enter
Sleep 5s
