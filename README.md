# Marginalia

## Book recommendation app

Marginalia is a full-stack book tracking app that combines content-based and collaborative filtering to suggest personalized recommendations. I built it for the **Client-side Internet Programming** course, bringing together my interest in books and software engineering.

Users can search for books, rate and review them, organize their reading, and explore why a book was recommended.

## Features

- Popular books on Discover, excluding books you have rated or marked as reading, finished, or set aside. Want-to-read books remain eligible.
- Personalized recommendations with three approaches: **Your personal mix**, **Themes you gravitate toward**, and **Reader connections**. Source-book filters show which recommendations a particular rated book contributed to.
- Title/author search, sorted by rating count or best match, and semantic search for themes and ideas.
- Book details, similar books, ratings, and editable reviews.
- Private reading shelves: want to read, reading, finished, and set aside. Switch between a grid and an optional CSS 3D bookshelf; known page counts influence spine thickness.
- Public profiles with a bio and reviews, plus private reading statistics.
- Registration and login using HTTP-only JWT cookies, with access-token refresh.

## Stack

| Part | Technology |
| --- | --- |
| Frontend | Vue 3 Composition API, JavaScript, Vue Router, Pinia, Vite |
| Backend | Django, Django REST Framework, Simple JWT |
| Database | PostgreSQL 16 with pgvector, running in Docker |
| Embeddings | Sentence Transformers, `all-MiniLM-L6-v2` (384 dimensions) |
| Collaborative filtering | NumPy and SciPy sparse matrices |
| Cache | Django database cache |

Docker runs the database. Django and Vite run separately on the host machine. Python dependencies are pinned in `requirements.txt`; frontend versions are recorded in `frontend/package-lock.json`.

## Local setup

These steps build a **new local database**. An existing installation does not need to re-import the catalog every time it starts.

### 1. Prerequisites and repository

Use Python 3.14, Docker with Compose, and a Node.js version supported by `frontend/package.json` (`^22.18.0` or `>=24.12.0`). The commands below use Windows PowerShell.

```powershell
git clone https://github.com/ibrahimferizi/Marginalia.git
cd Marginalia
mkdir datasets
```

### 2. Download the datasets

Download the following files through the [UCSD Goodreads dataset website](https://mengtingwan.github.io/data/goodreads.html), linked from the [authors' repository](https://github.com/MengtingWan/goodreads), and place them in `datasets/`:

| File | Purpose |
| --- | --- |
| `goodreads_books.json.gz` | Book metadata, descriptions, edition/work identifiers, page counts, and seed ratings |
| `goodreads_book_authors.json.gz` | Author names |
| `goodreads_book_genres_initial.json.gz` | Genre metadata |
| `goodreads_interactions.csv` | Historical user–book ratings for collaborative filtering |
| `book_id_map.csv` | Maps interaction CSV book IDs to the original Goodreads book IDs |

Keep the three JSON files compressed. The CSV files must be extracted. The ID map is required: interaction IDs are not interchangeable with catalog IDs.

The source files occupy roughly 6.5 GB before the database, model download, and generated matrix cache. The full collaborative build needs substantial RAM and can take a long time; runtime depends on the machine. The authors recommend 32 GB or more for their full-interaction exploration notebooks, rather than promising a small-memory build.

**The dataset authors permit academic use only and prohibit redistribution and commercial use.** Download the data from their source; do not commit datasets, matrix caches, or populated database exports. See the citations below.

### 3. Python environment

From the repository root:

```powershell
py -3.14 -m venv backend/.venv
./backend/.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux, create the environment with `python3.14 -m venv backend/.venv` and activate it with `source backend/.venv/bin/activate`.

Marking `backend` as a source root in an IDE is optional; it is not required to run Django.

### 4. Environment variables

From the repository root, copy the example files for Docker Compose and Django (first-time setup only):

```powershell
cp .env.example .env
cp backend/.env.example backend/.env
```

Edit the copied files. Set `POSTGRES_PASSWORD` in the root `.env` and `DB_PASSWORD` in `backend/.env` to the same local database password. Replace `SECRET_KEY` in `backend/.env` with a generated key. The other values match the default local setup.

Generate a Django secret key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Quote the generated value when placing it in `backend/.env`. Both `.env` files are ignored by Git; the `.env.example` templates are included in the repository. Their database names, users, and passwords must agree. If you already have working `.env` files, keep them rather than copying over them.

`GOOGLE_BOOKS_API_KEY` is for optional ISBN-based metadata enrichment. Core catalog search and recommendations use the imported data and local model. Google Books lookups need network access; failed lookups leave existing metadata intact.

### 5. Start the database and initialize Django

From the repository root, with Docker running:

```powershell
docker compose up -d
docker compose ps
cd backend
python manage.py migrate
python manage.py createcachetable
```

Wait for PostgreSQL to accept connections before migrating. The migrations enable pgvector and create the application tables and vector index. `createcachetable` creates the separate table used by Django's database cache.

### 6. Build the catalog and recommendation data

Run these commands in `backend/`, with the Python environment active, in this order:

```powershell
python manage.py import_books ../datasets/goodreads_books.json.gz ../datasets/goodreads_book_authors.json.gz ../datasets/goodreads_book_genres_initial.json.gz
python manage.py find_duplicate_editions
python manage.py generate_book_embeddings
python manage.py build_item_similarity ../datasets/goodreads_interactions.csv --book-id-map ../datasets/book_id_map.csv --matrix-cache ../datasets/cf_matrix.npz
```

- `import_books` defaults to a weighted random sample of 200,000 source records, favoring books with more ratings. Invalid or unusable records are skipped, so the final catalog is smaller. It includes page counts where available. A fresh import will not produce the exact same sample as another installation; rerunning it can add more books.
- `find_duplicate_editions` links likely duplicate editions using normalized title/author and ISBN. It keeps the most-rated entry as canonical. This is a heuristic, so some editions remain separate.
- `generate_book_embeddings` downloads MiniLM on first use and generates embeddings for canonical books. Existing embeddings are skipped unless `--force` is supplied. A GPU is optional.
- `build_item_similarity` translates CSV IDs, pools ratings for editions linked to a canonical book, and uses all matching 1–5-star interactions by default. Multiple ratings by the same historical user for a canonical book are averaged. The resulting neighbors are stored in PostgreSQL.

The optional matrix cache avoids rereading and rebuilding the full interaction matrix when its input fingerprint still matches. Neighbor computation still runs. This cache is not required to serve the app.

For a smaller trial build, use `import_books ... --sample-size 10000` and `build_item_similarity ... --sample-size 1000000`. These change the available books and collaborative coverage; they are not equivalent to the full build. Lowering `--block-size` can reduce similarity-computation memory, but the interaction matrix still has to fit in memory.

### 7. Start the app

In the backend terminal:

```powershell
python manage.py runserver 127.0.0.1:8000
```

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/** and register an account. Rate some books to build a personal recommendation profile. The source dataset's anonymous users are not imported as login accounts, and demo accounts are not included in a fresh setup.

Use `127.0.0.1` consistently for the frontend and backend so cookie authentication works as expected. Vite uses port 5173 and stops if that port is occupied. If you deliberately change addresses, configure `VITE_API_BASE_URL` in `frontend/.env` and `CORS_ALLOWED_ORIGINS` in `backend/.env` accordingly.

For later sessions, start Docker, activate the Python environment, and start Django and Vite. The database persists in Docker's `postgres_data` volume. Do not remove that volume unless you intend to discard the database, including accounts, ratings, and shelves.

### Maintenance and checks

These commands are separate because they solve different tasks and can be rerun independently:

| Command, run in `backend/` | When to use it |
| --- | --- |
| `python manage.py import_page_counts ../datasets/goodreads_books.json.gz` | Fill missing page counts in an older import; supports `--dry-run` |
| `python manage.py find_duplicate_editions --dry-run` | Inspect proposed edition links before applying them |
| `python manage.py generate_book_embeddings --book-id 123 --force` | Re-embed a specific database book ID after changing its text |
| `python manage.py backfill_taste_embeddings` | Recalculate preferences for existing accounts with reviews; unnecessary for a fresh installation with no reviews |
| `python manage.py check` | Check Django configuration |
| `python manage.py makemigrations --check --dry-run` | Check whether model changes need migrations |

After changing the imported catalog or canonical edition links, rebuild the affected embeddings and collaborative neighbors before relying on recommendations. Normal rating/review changes update user preferences automatically.

Run `npm run build` in `frontend/` to check the production frontend build. Local development checks and experiments are not distributed with the repository.

## How recommendations work

### Content-based score

A book's title, genre names, and description are combined and embedded using `all-MiniLM-L6-v2`. MiniLM is used as a pretrained encoder; it is not trained on this project's ratings.

The user's taste embedding is the rating-weighted mean of the available embeddings of books they rated:

```text
taste(u) = sum(rating(u, b) * embedding(b)) / sum(rating(u, b))
CB(u, candidate) = cosine(taste(u), embedding(candidate))
```

All 1–5-star ratings can contribute to this profile. Higher ratings contribute more; low ratings are weak positive weights, not explicit negative preferences.

### Collaborative score

An offline build computes item-to-item cosine similarity between historical rating columns. By default, books need at least five raters, pairs need five shared raters, and up to 15 neighbors are retained. Neighbors must pass both a 0.05 minimum similarity and 60% of the book's best eligible similarity.

At recommendation time, a user's rated books become seeds. Duplicate seed works are consolidated, keeping the highest rating. Seed weights are:

| User's rating | Collaborative seed weight |
| --- | --- |
| 1 or 2 | 0 |
| 3 | 0.2 |
| 4 | 0.8 |
| 5 | 1.0 |

Weighted neighbor similarities are summed for each eligible candidate, normalized by the largest candidate sum, and scaled by the strongest seed weight that has usable neighbors:

```text
support(u, b) = sum(seed_weight(u, s) * item_similarity(s, b))
CF(u, b) = confidence(u) * support(u, b) / max_candidate_support(u)
```

If there is no collaborative support, its score is zero. This is item-based collaborative filtering from the imported ratings, not a comparison between currently registered Marginalia users.

### Hybrid formula

```text
score(u, b) = alpha * CB(u, b) + (1 - alpha) * CF(u, b)
```

- `alpha = 0.70` when at least two distinct seed works rated 4 or 5 have usable collaborative neighbors.
- `alpha = 0.85` when collaborative support exists but fewer than two such strong seeds are available.
- `alpha = 1.00` when there is no collaborative support.
- Without a taste embedding, the hybrid uses only collaborative support (`alpha = 0`).

The content-only and collaborative-only approaches use `alpha = 1` and `alpha = 0`, respectively. These are ranking scores, not predicted star ratings or probabilities.

Candidates combine the 500 nearest content matches with collaborative neighbors. Positive-scoring candidates are ordered by score, then rating count and book ID for ties. Already-rated works and detected study aids are excluded; results are deduplicated by work and prefer an available English edition. Unrated books on a reading shelf may still appear in personalized recommendations.

The explanations are generated from the scoring paths and contributing seed books using fixed text. There is no LLM generating explanations. Source-book filters use all contributing collaborative seeds, including contributions beyond the strongest one.

Personal recommendations are cached. Exploration caches each approach for up to one hour, so source filtering and pagination can reuse the ranking. Adding, editing, or deleting a review invalidates that user's recommendation caches. Rebuilding embeddings or collaborative neighbors clears caches too. A first uncached request can take longer.

### Similar books and semantic search

A book's similar-books shelf uses its precomputed collaborative neighbors, with genre-vector similarity as a fallback when usable neighbors are missing. It is the same for all readers.

Semantic search embeds the query with the same MiniLM model, ranks a shortlist of 200 content matches plus exact-title matches, and deduplicates works. Best match prioritizes exact titles; Most popular sorts the matching shortlist by rating count. It does not perform general language reasoning, and a theme query can return both fiction and nonfiction.

Distances are calculated in PostgreSQL with pgvector. The schema includes an HNSW index, but the current recommendation/search candidate query deliberately orders by an exact similarity expression; the presence of the index does not mean every query uses approximate HNSW search.

## Current limits

- A new account has no personal taste history. Popular books provide a starting point; hybrid recommendations reduce dependence on either signal but do not eliminate cold start.
- This is a sampled, historical catalog. Missing descriptions, page counts, translated editions, and imperfect edition linking affect results.
- Broadly popular books and heavily rated series can dominate collaborative connections. The model does not explicitly diversify results or enforce series reading order.
- Public profiles are implemented; following readers, taste-matched users, notifications, and badges are not.
- The app is configured for local development, including `DEBUG=True`. Public deployment needs production settings and a review of data-use, API attribution, and security requirements.

## Data, model, and references

### Goodreads / UCSD

Book data and historical interactions come from the [Goodreads datasets collected by Mengting Wan and collaborators](https://github.com/MengtingWan/goodreads). Their repository requests both citations:

1. Mengting Wan and Julian McAuley. **Item Recommendation on Monotonic Behavior Chains.** RecSys, 2018. [Paper and dataset reference](https://github.com/MengtingWan/goodreads#citations).
2. Mengting Wan, Rishabh Misra, Ndapa Nakashole, and Julian McAuley. **Fine-Grained Spoiler Detection from Large-Scale Review Corpora.** ACL, 2019, pp. 2605–2610. [Paper](https://aclanthology.org/P19-1248/).

The dataset's academic-use restrictions apply independently of the Apache-2.0 license on the authors' code samples. Book covers and descriptions remain third-party content.

### Embedding model

[Sentence Transformers: all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) is distributed under Apache-2.0. Its model card describes 384-dimensional embeddings and truncation beyond 256 word pieces. Preserve the model's license notices when redistributing model files.

Nils Reimers and Iryna Gurevych. **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.** EMNLP-IJCNLP, 2019. [Paper](https://aclanthology.org/D19-1410/).

### Research background

The initial research explored hybrid recommendation methods. These are background references, not claims that Marginalia reproduces their architectures or reported results:

- Qingna Pu and Bin Hu. **Intelligent Movie Recommendation System Based on Hybrid Recommendation Algorithms.** AIKIIE, 2023. [DOI](https://doi.org/10.1109/AIKIIE60097.2023.10389982).
- Amany Sami, Waleed El Adrousy, Shahenda Sarhan, and Samir Elmougy. **A deep learning based hybrid recommendation model for internet users.** Scientific Reports 14, 29390, 2024. [Paper](https://www.nature.com/articles/s41598-024-79011-z).
- Anvi Vats, Yamini Agrawal, and Neha Tyagi. **A Hybrid Book Recommendation System Using Collaborative Filtering and Content-Based Filtering with Neural Embeddings.** 2025 IEEE 7th International Conference on Computing, Communication and Automation (ICCCA), 2025. [DOI](https://doi.org/10.1109/ICCCA66364.2025.11325340).
- Steffen Rendle, Walid Krichene, Li Zhang, and John Anderson. **Neural Collaborative Filtering vs. Matrix Factorization Revisited.** RecSys, 2020. [Paper](https://research.google/pubs/neural-collaborative-filtering-vs-matrix-factorization-revisited/). Background reading for earlier matrix-factorization experiments; the current collaborative component uses item similarity instead.

### Metadata and visual inspiration

Optional missing-cover and description enrichment uses the [Google Books API](https://developers.google.com/books), subject to its [terms](https://developers.google.com/books/terms) and [attribution guidelines](https://developers.google.com/books/branding). Books linked to Google Books display its official attribution badge and a link to the corresponding Google Books page beneath their covers.

Visual references: [Carollia's virtual library](https://carollia-library.lovable.app/) and [build guide](https://github.com/carollia99/virtual-library-guide), [time&space Book Corner](https://www.timeand-space.co/bookcorner), and [Stripe Press](https://press.stripe.com/). Marginalia implements its own Vue/CSS shelf and page layouts; these links credit the visual inspiration.

## License

Marginalia's original code and documentation are licensed under the [MIT License](LICENSE). Copyright (c) 2026 Ibrahim Ferizi.

Third-party datasets, book covers and descriptions, model weights, dependencies, and Google branding retain their respective licenses and terms. The MIT license does not override the Goodreads/UCSD dataset's academic-use restrictions.
