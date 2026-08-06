# Home page images

Drop your own PNGs here (transparent background recommended) with these
**exact filenames** - `components/HomeView.js` already references them, and
gracefully falls back to a plain SVG icon for anything missing, so you can
add these one at a time without ever breaking the page.

| Filename | Where it shows up | Suggested size |
|---|---|---|
| `hero.png` | The big theme image in the center | ~800×800, roughly square, transparent or on its own backdrop |
| `icon-light.png` | Floating button at the **top** of the hero image - toggles light/dark mode | ~200×200, transparent |
| `icon-wiki.png` | Floating button beside the hero - opens the Knowledge base view | ~200×200, transparent |
| `icon-calendar.png` | Floating button beside the hero - opens the Calendar view | ~200×200, transparent |
| `icon-weather.png` | Floating button beside the hero - opens Calendar (where the weather widget lives) | ~200×200, transparent |

All the small icons render inside circular buttons with `object-fit:
contain`, so a square image with the subject centered and transparent
padding around it works best - it'll get a soft drop-shadow and a gentle
floating animation automatically (see `.home-float` in `style.css`).

The hero image isn't cropped to a circle - it's shown in full via
`object-fit: contain`, so any aspect ratio works, though something close
to square fits the layout best.
