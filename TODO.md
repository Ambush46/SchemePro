# TODO

## Curriculum hierarchy UI updates
- [ ] Update `app/templates/admin.html`:
  - [ ] Subjects tab: change dropdown order to CurriculumSystem → Level → Sub-Level → (then add subject)
  - [ ] Topics tab: change to CurriculumSystem → Level → Sub-Level → Subject → Topic name
  - [ ] Subtopics tab: change to CurriculumSystem → Level → Sub-Level → Subject → Topic → Sub-topic name/content
  - [ ] Update JS helper functions used by those tabs to filter subjects using `/api/v1/subjects?level_id=&sublevel_id=&curriculum_system=`
- [x] Run `pytest` to ensure nothing broke
- [ ] Sanity-check manual UI flow in admin page


