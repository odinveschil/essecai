# A Tray at La Felicità

ESSEC Advanced Entrepreneurship, 2026.

The site opens on a tray of food on a communal table at La Felicità, Station F. The tray is the navigation:

| On the tray | Opens |
| --- | --- |
| Pizza slice: Seamone Paris | *Seamone Paris (read: See Money, Paris?)* |
| Pizza slice: Business Angels | *Angel Investors* |
| Pizza slice: Serena VC | *Serena VC* |
| Pizza slice: TOMCAT | *TOMCAT* |
| Pizza slice: Freeda | *Free-Dough? (read: FREEDA)* |
| Pizza slice: Station F | *Prochain arrêt, Station F* |
| Coke Zero (coaster: "Introduction") | **Video 1**: class introduction |
| Tiramisu (plate: "Station F — Film") | **Video 2**: Station F film |

## Run it

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # static site in dist/ (works from any folder or sub-path)
npm run preview
```

## Videos

Put the files in `public/videos/` and name them by number:

```
public/videos/1.mp4   → Coke Zero → class introduction
public/videos/2.mp4   → Tiramisu  → Station F film
```

`.mp4`, `.webm`, `.mov` and `.m4v` all work. Only the base filename (`1` or `2`) matters, and the first file that exists is the one that plays. To swap a video, replace the file. No code changes are needed.

**1 = Coke Zero = introduction. 2 = Tiramisu = Station F. Never the other way round.**

If a file is missing, the player shows "Video coming soon." If your host renames uploads, set an explicit `src` in `src/config/videos.ts`.

The current `1.mp4` and `2.mp4` are the uploaded originals, remuxed with `+faststart` so playback starts quickly. They were not re-encoded.

## Where things live

```
src/content/articles.ts      the six articles (final copy, verbatim)
src/config/videos.ts         video mapping (1 → introduction, 2 → Station F)
src/components/
  LaFelicitaScene.tsx        stage, responsive framing, parallax, opening settle
  RestaurantBackground.tsx   defocused hall, breathing bulbs, passers-by
  CommunalTable.tsx          table + tray plate
  FoodTray.tsx               slice / tiramisu / Coke layers, hover lift, SVG hit polygons
  AmbientSceneDetails.tsx    steam, vignette, grain
  ArticleModal.tsx           the article, printed like a menu
  VideoModal.tsx             native video player overlay
  Dialog.tsx                 Escape / click-outside / focus trap / scroll lock
src/scene/{desktop,mobile}.json   layer rects + hit polygons (generated)
public/scene/{desktop,mobile}/    rendered layers (generated, WebP @1x/@2x)
scene-render/                the Blender pipeline that produces the scene
```

## How the scene is made

No stock photography and no AI imagery. The whole scene is built and path-traced in Blender (Cycles, via the `bpy` Python module) from procedural geometry and textures generated in `scene-render/`:

- `tex_pizza.py`: the Neapolitan pizza (cornicione with leopard spotting, sauce, fior di latte, pepperoni, chicken, basil, oil). It also brands the six section names into the crust.
- `tex_misc.py`: oak communal table, kraft paper, worn tray, coaster, plate glaze print, receipt, notebook, signage.
- `scene.py`, `props.py`, `hall.py`: the table, tray, six separate slice meshes, tiramisu, Coke Zero (ice, condensation, bubbles), table clutter, and the Station F hall (concrete structure and skylights, kiosks and signs, the train carriage, festoon bulbs, plants, diners).
- `passes.py`: renders a sharp foreground, a heavily defocused hall, a base plate with the clickable food removed (shadows kept), and anti-aliased masks for every clickable object.
- `extract.py`: cuts out each slice, the tiramisu and the glass as their own layers, traces their hit polygons, finds the hall's light positions, and writes everything the web app reads.

Desktop (landscape) and mobile (portrait) are two separate camera set-ups. On mobile the camera looks down the length of the table.

To re-render (needs Python 3.11, roughly 2 hours on 4 CPU cores):

```bash
pip install bpy numpy scipy pillow fonttools brotli scikit-image
./scene-render/render_all.sh
```
