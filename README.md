# melaniesubbiah.github.io

Source for [melaniesubbiah.github.io](https://melaniesubbiah.github.io/). GitHub Pages serves the HTML files in the repo root straight from `main`.

The root `.html` files and `sitemap.xml` are **generated**. Edit the files in `src/` and `data/`, then rebuild:

```sh
python3 build.py              # needs only Python 3, no packages to install
python3 -m http.server        # preview at http://localhost:8000
```

Commit both the source files and the regenerated output. A GitHub Action (`.github/workflows/check-build.yml`) fails if the committed HTML is out of date with `src/` and `data/`.

## Adding a publication

1. On Google Scholar, click **Cite → BibTeX** under the paper and copy the entry.
2. Paste it anywhere in `data/publications.bib`. Entries are sorted by year automatically.
3. Optionally add any of these fields to the entry:
   - `venue = {EMNLP 2026}` sets a short venue label. Without it, the label is guessed from the booktitle or journal.
   - `award = {Best Paper Award}` adds a highlighted badge.
   - `selected = {true}` and `blurb = {...}` mark a paper as a highlight with a one-sentence summary. They're not shown anywhere right now; put `{{ selected }}` in a page to list them.
   - `tags = {Narrative, Psychology & mental health}` sets the paper's research themes, written exactly as they should appear on the site. Each tag gets a colored dot next to the paper, a pill in "Research themes" on the homepage, and a filter button on the publications page. Reuse an existing tag (capitalization doesn't matter) to add the paper to that theme. A tag you haven't used before becomes a new theme automatically, with the next free color, so no other file needs editing. The current tags are Psychology & mental health, Interpretability & steering, Safety & fairness and Narrative. To change the order they're shown in, edit `THEME_ORDER` near the top of `build.py`; tags not listed there come after, in the order they first appear in the .bib.
   - `url`, `pdf`, `code`, `data`, `slides`, `poster` and `video` add links. The first link also makes the title clickable.
   - Mark equal contribution with `*` after the surname: `Subbiah*, Melanie`.
4. Run `python3 build.py` and commit.

Google Scholar has no official API and blocks automated scraping, so import is copy-paste rather than automatic.

## Editing other content

| What | Where |
| --- | --- |
| Homepage: research statement, themes, path, honors | `src/index.html` |
| Teaching and mentoring | `src/teaching.html` |
| Header, nav, footer, page `<head>` | `src/_layout.html` |
| Colors, fonts, layout | `assets/css/style.css` (color tokens are at the top, with dark-mode values below them) |
| CV | replace `assets/cv-melaniesubbiah.pdf`, keeping the filename |

Each `src/` page begins with a small `---` block that sets its `title`, `description` (used for search results and link previews) and which `nav` item is highlighted.

## Adding news

News on the homepage is a hand-written list in `src/index.html` (the `<section id="news">` block), newest first. To add an item, copy a line and put it at the top:

```html
<li><span class="when">Nov 2026</span><span class="news-text">New preprint: <a href="https://arxiv.org/abs/..." target="_blank" rel="noopener"><em>Paper title</em></a>.</span></li>
```

Keep all the text inside the one `news-text` span, or links and italics get squeezed into their own columns. Good candidates: papers accepted to a venue, awards and grants, invited talks, media, and job news. Preprints don't go in News; they show up on the publications page. Keep only the five most recent items.

## Mentee flow diagram

The flow diagram on the teaching page is drawn by `build.py` from the `MENTEES` list near the top of that file: one line per student with the stages they went through, left to right (Undergrad, Master's, then Paper or Thesis, then Ph.D. or Industry). A student can skip a stage, e.g. an undergrad who went straight to a paper. `FLOW_COLUMNS` sets which column each stage is in and the top-to-bottom order. Edit the list and rebuild. Names aren't shown on the page; the diagram only shows counts, with a color key for undergrad vs. master's.

## Updating the headshot

Two files are involved, both square crops of the original photo:

- `assets/img/MelanieS--3square.jpg` (1200 px) is the link-preview image (`og:image` in `src/_layout.html`).
- `assets/img/portrait.jpg` (800 px) is the homepage photo.

To use a different photo:

1. Put the original in the repo folder. Originals in the repo root are git-ignored (see `.gitignore`), so the large file isn't committed.
2. Make the two square copies. For example, with Pillow, starting the crop near the top of the photo so the head isn't cut off:
   ```sh
   python3 -c "from PIL import Image, ImageOps; im = ImageOps.exif_transpose(Image.open('NEW.jpg')).convert('RGB'); w = im.width; sq = im.crop((0, 120, w, 120 + w)); sq.resize((1200, 1200)).save('assets/img/MelanieS--3square.jpg', quality=82); sq.resize((800, 800)).save('assets/img/portrait.jpg', quality=82)"
   ```
   Don't use `sips -c`. It always crops from the center, which cuts off the top of a portrait.
3. If you renamed the large copy, update `og:image` in `src/_layout.html`. Then rebuild.

## The dogs in the header

The header has two dogs, Mango and Luna:

- **Mango** (`assets/img/dog-1.svg`) sits next to the name. He's also the browser-tab icon, and has a thin cream outline so his black coat shows on the olive.
- **Luna** (`assets/img/dog-2.svg`) stands in front of whichever page you're on in the nav. `build.py` inserts her using the `NAV_DOG` snippet near the top of the file.

Clicking either dog opens the dogs page, `dogs.html` (source: `src/dogs.html`), at the top, with the photo of the dog you clicked outlined in yellow. On the dogs page itself, Luna stands just to the right of the name. The photos are `assets/img/mango.jpg` and `assets/img/luna.jpg`. The icons are hand-drawn, side-view SVGs based on those photos, so edit the SVGs directly to tweak markings or colors.

Mango trots in once per visit, Luna hops when a page loads, and both hop on hover. All of these animations are turned off for visitors who have reduced motion enabled.

## The handwritten name

The name in the header and footer is the user's handwriting, saved as two transparent PNGs of just the ink:

- `assets/img/signature-header.png`: cream (`#FBF6EC`, the header text color) with a heavier stroke, for the olive header.
- `assets/img/signature-dark.png`: dark ink, for the footer. It's inverted in dark mode.

The contact email in the homepage sidebar and the footer is handwritten the same way (`assets/img/email-dark.png`, dark ink, inverted in dark mode); its `alt` text is the address itself, and it's still a `mailto:` link.

Each name `<img>` has `alt="Melanie Subbiah"`, so screen readers and search engines still get the name.

To redo it from a new photo of your handwriting, write the name in dark pen on plain or lined paper and photograph it flat in even light. Then crop the photo to the name and remove the paper and any ruled lines so only the ink is left. To get the current even, digital-pen look, trace each stroke's center line and redraw it at one fixed width, so faint parts of the photo don't show up as faded. Save a cream copy for the header (with a heavier pen) and a dark copy for the footer, both with transparent backgrounds. If the new images have a different shape, update the `width`/`height` attributes on the two `<img>` tags in `src/_layout.html`.
