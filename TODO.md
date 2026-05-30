# TODO

## Curriculum hierarchy alignment (Education system → class/grade → subject → topic → subtopic/content)

### Step 1: Inspect code paths that generate curriculum JSON
- [ ] Locate controllers/services that fetch curriculum/subjects/topics/subtopics/content
- [ ] Identify current API response structure

### Step 2: Update DB models
- [ ] Update `app/models/level.py` to include `curriculum_system` (CBC/844)
- [ ] Update `app/models/subject.py` to add `sublevel_id` and relationship
- [ ] Adjust topic/subtopic/content relationships if needed

### Step 3: Migrations
- [ ] Create Alembic migration to add new columns and constraints
- [ ] Handle backfill / compatibility strategy for existing data

### Step 4: Update queries & API responses
- [ ] Modify controllers/services to query by `sublevel_id` and include system
- [ ] Ensure JSON hierarchy matches requested order

### Step 5: Tests & smoke run
- [ ] Run `pytest`
- [ ] Run migrations and smoke-check endpoints

