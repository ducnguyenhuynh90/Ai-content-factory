# video-editor configuration (edit freely)

- `brand.json` — primary_color, secondary_color (#RRGGBB), font (a HyperFrames bundled font name such as
  Montserrat/Poppins/Inter, a system font name, or a path to a .ttf/.otf/.woff2), optional logo, caption_accent,
  text_color. Created only from what you tell the editor; it never invents one.
- `preferences.json` — stable defaults: platform, cta, style, pace (tight|natural|relaxed), caption_words,
  caption_size (multiplier), caption_case, emphasis, jump_cuts, emojis, workspace.
- `taste.json` — your feedback in your own words ("you said"), kept apart from rules the editor learned itself.

Change them by hand or with `ve brand set ...`, `ve pref KEY VALUE`, `ve taste "what you said" --set key=value`.
