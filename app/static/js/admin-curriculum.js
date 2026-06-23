/**
 * Admin Curriculum Management Module
 * Handles levels, sublevels, subjects, topics, and subtopics
 */

/**
 * Render curriculum content management
 */
function renderContent(main) {
  main.innerHTML = `
    <h1>🗂 Curriculum Content Management</h1>
    <div class="tab-btns">
      <button class="tab-btn active" onclick="switchContentTab('levels',this)">Levels</button>
      <button class="tab-btn" onclick="switchContentTab('subjects',this)">Subjects</button>
      <button class="tab-btn" onclick="switchContentTab('topics',this)">Topics</button>
      <button class="tab-btn" onclick="switchContentTab('subtopics',this)">Sub-Topics / Content</button>
    </div>
    <div id="content-tab"></div>`;
  switchContentTab('levels', document.querySelector('.tab-btn'));
}

/**
 * Switch between curriculum tabs
 */
async function switchContentTab(tab, el) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  el?.classList.add('active');
  const c = document.getElementById('content-tab');

  try {
    if (tab === 'levels') await loadLevelsTab(c);
    if (tab === 'subjects') await loadSubjectsTab(c);
    if (tab === 'topics') await loadTopicsTab(c);
    if (tab === 'subtopics') await loadSubtopicsTab(c);
  } catch (error) {
    c.innerHTML = `<div class="alert alert-error">Error loading ${tab}: ${error.message}</div>`;
  }
}

/**
 * Load levels tab content
 */
async function loadLevelsTab(container) {
  const [res, curriculum] = await Promise.all([
    API.get('/api/v1/levels'),
    API.get('/api/v1/curriculum-systems')
  ]);

  const levelsList = (res.data || []).map(l => `
    <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--gray-100);font-size:13px">
      <span style="flex:1;font-weight:500">${l.name}</span>
      <code style="background:var(--gray-100);padding:2px 8px;border-radius:4px;font-size:11px">${l.tag}</code>
      <span class="badge badge-blue">${l.curriculum_system || '—'}</span>
      <span class="text-muted">${l.sublevels?.length||0} sub-levels</span>
      <div style="display:flex;gap:6px">
        <button class="btn btn-sm" onclick="editLevel(${l.id})">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteLevel(${l.id},'${l.name.replace(/'/g, "\\'")}')">Delete</button>
      </div>
    </div>`).join('');

  container.innerHTML = `
    <div class="card">
      <div class="card-title">Add Curriculum System</div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Curriculum Name</label>
          <input class="form-input" id="new-curriculum-name" placeholder="e.g. Competency Based Education">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="new-curriculum-tag" placeholder="e.g. cbc">
        </div>
        <button class="btn btn-primary" onclick="addCurriculum()">Add Curriculum</button>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Add Level</div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Level Name</label>
          <input class="form-input" id="new-level-name" placeholder="e.g. Junior School (CBC)">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="new-level-tag" placeholder="e.g. junior_cbc">
        </div>
        <div class="form-group">
          <label class="form-label">Curriculum System</label>
          <select class="form-input form-select" id="new-level-system">
            ${curriculum.data.map(l=>`<option value="${l.id}">${l.name} — ${l.tag}</option>`).join('')}
          </select>
        </div>
        <button class="btn btn-primary" onclick="addLevel()">Add Level</button>
      </div>
    </div>
    <div class="card" style="margin-top:1rem">
      <div class="card-title">Add Sub-Level</div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Level</label>
          <select class="form-input form-select" id="new-sublevel-level">
            ${res.data.map(l=>`<option value="${l.id}">${l.curriculum_system} — ${l.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sub-Level Name</label>
          <input class="form-input" id="new-sublevel-name" placeholder="e.g. Form 3">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="new-sublevel-tag" placeholder="e.g. form_3">
        </div>
        <button class="btn btn-primary" onclick="addSublevel()">Add Sub-Level</button>
      </div>
    </div>
    <hr>
    <div class="card-title" style="margin-top:1rem">Existing Levels</div>
    <div style="font-size:12px;color:var(--gray-500);margin-bottom:10px">Edit or delete levels (delete removes sublevels/subjects/topics downstream).</div>
    ${levelsList}
  </div>`;
}

/**
 * Load subjects tab content
 */
async function loadSubjectsTab(container) {
  const [systemsRes, levelsRes, subjRes] = await Promise.all([
    API.get('/api/v1/curriculum-systems'),
    API.get('/api/v1/levels'),
    API.get('/api/v1/subjects')
  ]);
  const systems = systemsRes.data || [];

  const subjectsList = (subjRes.data || []).map(s => `
    <div style="padding:8px;background:var(--gray-50);border-radius:var(--radius);font-size:13px">
      <strong>${s.name}</strong> <span class="badge badge-blue">${s.curriculum_system}</span>
      <div class="text-muted" style="font-size:11px">${s.level_name}</div>
      <div class="text-muted" style="font-size:11px">${s.sublevel_name}</div>
      <div style="display:flex;gap:6px;margin-top:6px">
        <button class="btn btn-sm" onclick="editSubject(${s.id})">Edit</button>
        <button class="btn btn-sm btn-danger" onclick="deleteSubject(${s.id},'${s.name.replace(/'/g, "\\'")}')">Delete</button>
      </div>
    </div>`).join('');

  container.innerHTML = `
    <div class="card">
      <div class="card-title">Add Subject</div>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Subject Name</label>
          <input class="form-input" id="new-subj-name" placeholder="e.g. Agriculture">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="new-subj-tag" placeholder="e.g. agriculture_senior">
        </div>
        <div class="form-group">
          <label class="form-label">Curriculum System</label>
          <select class="form-input form-select" id="new-subj-system" onchange="loadLevelsForSubjectSystem()">
            ${systems.map(s=>`<option value="${s.name}">${s.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Level</label>
          <select class="form-input form-select" id="new-subj-level" onchange="loadSublevelsForSubject()">
            <option value="">Select curriculum system first</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sub-Level</label>
          <select class="form-input form-select" id="new-subj-sublevel">
            <option>Grade or Classes (select Level first)</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" onclick="addSubject()">Add Subject</button>
    </div>
    <hr>
    <div class="card-title" style="margin-top:1rem">All Subjects (${subjRes.data.length})</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
      ${subjectsList}
    </div>
  </div>`;

  setTimeout(() => loadLevelsForSubjectSystem(), 0);
}

/**
 * Load topics tab content
 */
async function loadTopicsTab(container) {
  const [levelsRes, systemRes] = await Promise.all([
    API.get('/api/v1/levels'),
    API.get('/api/v1/curriculum-systems')
  ]);
  const systems = systemRes.data || [];
  const levels = levelsRes.data || [];

  container.innerHTML = `
    <div class="card">
      <div class="card-title">Add Topic / Strand</div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Curriculum System</label>
          <select class="form-input form-select" id="new-topic-system" onchange="loadLevelsForTopics(this.value)">
            ${systems.map(s=>`<option value="${s.name}">${s.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Level</label>
          <select class="form-input form-select" id="new-topic-level" onchange="loadSublevelsForTopics(this.value)">
            ${levels.map(l=>`<option value="${l.id}">${l.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sub-Level</label>
          <select class="form-input form-select" id="new-topic-sublevel" onchange="loadSubjectsForAdminTopics()">
            <option value="">All sub-levels</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Subject</label>
          <select class="form-input form-select" id="new-topic-subj" onchange="loadTopicsForAdmin(this.value)">
            <option value="">Select system/level/sub-level first</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Topic / Strand Name</label>
          <input class="form-input" id="new-topic-name" placeholder="e.g. Linear Motion">
        </div>
        <button class="btn btn-primary" onclick="addTopic()">Add Topic</button>
      </div>
      <div style="margin-top:8px;font-size:12px;color:var(--gray-500)">
        Curriculum System → Level → Sub-Level → Subject.
      </div>
      <hr>
      <div id="existing-topics"><p class="text-muted text-sm">Select a subject to view topics.</p></div>
    </div>`;

  setTimeout(() => loadLevelsForTopics(document.getElementById('new-topic-system')?.value), 0);
}

/**
 * Load subtopics/content tab content
 */
async function loadSubtopicsTab(container) {
  const [levelsRes, systemRes] = await Promise.all([
    API.get('/api/v1/levels'),
    API.get('/api/v1/curriculum-systems')
  ]);
  const systems = systemRes.data || [];
  const levels = levelsRes.data || [];

  container.innerHTML = `
    <div class="card">
      <div class="card-title">Add Sub-Topic / Content</div>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Curriculum System</label>
          <select class="form-input form-select" id="st-system" onchange="loadLevelsForST(this.value)">
            ${systems.map(s=>`<option value="${s.name}">${s.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Level</label>
          <select class="form-input form-select" id="st-level" onchange="loadSublevelsForST(this.value)">
            ${levels.map(l=>`<option value="${l.id}">${l.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sub-Level</label>
          <select class="form-input form-select" id="st-sublevel" onchange="loadSubjectsForST()">
            <option value="">All sub-levels</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Subject</label>
          <select class="form-input form-select" id="st-subj" onchange="loadTopicsForST(this.value)">
            <option value="">Select subject</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Topic</label>
          <select class="form-input form-select" id="st-topic"><option>Select subject first</option></select>
        </div>
        <div class="form-group form-full">
          <label class="form-label">Sub-Topic Name</label>
          <input class="form-input" id="new-st-name" placeholder="e.g. Newton's First Law">
        </div>
        <div class="form-group">
          <label class="form-label">Teaching Content / Aids</label>
          <input class="form-input" id="new-st-content" placeholder="e.g. Spring balance, weights">
        </div>
        <div class="form-group">
          <label class="form-label">Teaching Activities</label>
          <input class="form-input" id="new-st-activities" placeholder="e.g. Reading and writing">
        </div>
        <div class="form-group">
          <label class="form-label">Learning Outcomes</label>
          <input class="form-input" id="new-st-learning-outcomes" placeholder="e.g. The learner should be able to state Hooke's law">
        </div>
        <div class="form-group">
          <label class="form-label">References</label>
          <input class="form-input" id="new-st-refernces" placeholder="e.g. Master page 2">
        </div>
        <div class="form-group">
          <label class="form-label">No. of Lessons</label>
          <input class="form-input" type="number" id="new-st-lessons" value="2" min="1" max="20">
        </div>
        <div class="form-group form-full">
          <label class="form-label">Key Inquiry Question (CBC)</label>
          <input class="form-input" id="new-st-kiq" placeholder="e.g. Why do objects resist changes in motion?">
        </div>
      </div>
      <button class="btn btn-primary" onclick="addSubTopic()">Add Sub-Topic</button>
      <div id="st-feedback" class="alert alert-success" style="display:none;margin-top:8px"></div>
    </div>`;

  setTimeout(() => loadLevelsForST(document.getElementById('st-system')?.value), 0);
}

/* ─────────────────────────────────────────────────
   Curriculum CRUD Operations
   ───────────────────────────────────────────────── */

async function addCurriculum() {
  const name = document.getElementById('new-curriculum-name').value.trim();
  const tag = document.getElementById('new-curriculum-tag').value.trim();
  if (!name || !tag) return showNotification('Name and tag are required.', 'error');
  await API.post('/api/v1/curriculum-systems', { name, tag });
  switchContentTab('levels', document.querySelector('.tab-btn'));
  showNotification('Curriculum added!', 'success');
}

async function addLevel() {
  const name = document.getElementById('new-level-name').value.trim();
  const tag = document.getElementById('new-level-tag').value.trim();
  const curriculum_system = document.getElementById('new-level-system')?.value || '844';
  if (!name || !tag) return showNotification('Name and tag are required.', 'error');
  await API.post('/api/v1/levels', { name, tag, curriculum_system });
  switchContentTab('levels', document.querySelector('.tab-btn'));
  showNotification('Level added!', 'success');
}

async function addSublevel() {
  const levelId = parseInt(document.getElementById('new-sublevel-level')?.value);
  const name = document.getElementById('new-sublevel-name')?.value.trim();
  const tag = document.getElementById('new-sublevel-tag')?.value.trim();
  if (!levelId || !name || !tag) return showNotification('Level, name and tag are required.', 'error');
  await API.post('/api/v1/sublevels', { level_id: levelId, name, tag });
  showNotification('Sub-level added!', 'success');
  switchContentTab('levels', document.querySelector('.tab-btn'));
}

async function editLevel(levelId) {
  const levels = await API.get('/api/v1/levels');
  const lvl = (levels.data || []).find(l => String(l.id) === String(levelId));
  if (!lvl) return showNotification('Level not found.', 'error');

  openModal(`Edit Level — ${lvl.name}`, `
    <div class="card" style="box-shadow:none;border:1px solid var(--gray-200)">
      <div class="card-title">Level Details</div>
      <div class="form-row" style="grid-template-columns:1fr 1fr 1fr">
        <div class="form-group">
          <label class="form-label">Name</label>
          <input class="form-input" id="edit-level-name" value="${lvl.name.replace(/"/g,'"')}">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="edit-level-tag" value="${lvl.tag}">
        </div>
        <div class="form-group">
          <label class="form-label">System</label>
          <select class="form-input form-select" id="edit-level-system">
            <option value="844" ${lvl.curriculum_system==='844'?'selected':''}>844</option>
            <option value="CBC" ${lvl.curriculum_system==='CBC'?'selected':''}>CBC</option>
          </select>
        </div>
      </div>
      <div style="margin-top:12px;display:flex;gap:10px;align-items:center">
        <button class="btn btn-primary" onclick="saveEditLevel(${lvl.id})">Save</button>
        <div id="edit-level-error" class="alert alert-error" style="display:none;margin:0;padding:0.75rem 1rem;font-size:13px"></div>
      </div>
    </div>
  `);
}

async function saveEditLevel(levelId) {
  const errEl = document.getElementById('edit-level-error');
  if (errEl) errEl.style.display = 'none';
  const name = document.getElementById('edit-level-name')?.value?.trim();
  const tag = document.getElementById('edit-level-tag')?.value?.trim();
  const curriculum_system = document.getElementById('edit-level-system')?.value || '844';
  try {
    await API.put(`/api/v1/levels/${levelId}`, { name, tag, curriculum_system });
    closeModal();
    switchContentTab('levels', document.querySelector('.tab-btn'));
    showNotification('Level updated!', 'success');
  } catch (e) {
    if (errEl) {
      errEl.textContent = e.message || 'Unable to update level.';
      errEl.style.display = 'block';
    }
  }
}

async function deleteLevel(levelId, levelName) {
  if (!confirm(`Delete level "${levelName}"? This cannot be undone.`)) return;
  try {
    await API.delete(`/api/v1/levels/${levelId}`);
    switchContentTab('levels', document.querySelector('.tab-btn'));
    showNotification('Level deleted!', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to delete level', 'error');
  }
}

async function addSubject() {
  const sublevelRaw = document.getElementById('new-subj-sublevel')?.value || '';
  const body = {
    name: document.getElementById('new-subj-name').value.trim(),
    tag: document.getElementById('new-subj-tag').value.trim(),
    level_id: parseInt(document.getElementById('new-subj-level').value),
    sublevel_id: sublevelRaw ? parseInt(sublevelRaw) : null,
    curriculum_system: document.getElementById('new-subj-system').value,
  };
  if (!body.name || !body.tag) return showNotification('Name and tag required.', 'error');
  await API.post('/api/v1/subjects', body);
  showNotification('Subject added!', 'success');
  switchContentTab('subjects', document.querySelector('.tab-btn:nth-child(2)'));
}

async function editSubject(subjectid) {
  const systemsRes = await API.get('/api/v1/curriculum-systems');
  const subjectRes = await API.get('/api/v1/subjects');
  const systems = systemsRes.data || [];
  const subject = (subjectRes.data || []).find(s => String(s.id) === String(subjectid));
  if (!subject) return showNotification('Subject not found.', 'error');
  
  openModal(`Edit Subject — ${subject.name}`, `
    <div class="card" style="box-shadow:none;border:1px solid var(--gray-200)">
      <div class="card-title">Subject Details</div>
      <div class="form-row" style="grid-template-columns:1fr 1fr 1fr">
        <div class="form-group">
          <label class="form-label">Name</label>
          <input class="form-input" id="edit-level-name" value="${subject.name.replace(/"/g,'"')}">
        </div>
        <div class="form-group">
          <label class="form-label">Tag</label>
          <input class="form-input" id="edit-level-tag" value="${subject.tag}">
        </div>
        <div class="form-group">
          <label class="form-label">System</label>
          <select class="form-input form-select" id="edit-subject-system" onchange="loadEditLevelsForSubjectSystem()">
            <option value="${subject.curriculum_system}" selected>${subject.curriculum_system}</option>
            ${systems.map(s=>`<option value="${s.name}">${s.name}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Level</label>
          <select class="form-input form-select" id="edit-subject-level">
            <option value="${subject.level_id}" selected>${subject.level_name}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Sub Level</label>
          <select class="form-input form-select" id="edit-subject-sublevel">
            <option value="${subject.sublevel_id}" selected>${subject.sublevel_name}</option>
          </select>
        </div>
      </div>
      <div style="margin-top:12px;display:flex;gap:10px;align-items:center">
        <button class="btn btn-primary" onclick="saveEditSubject(${subject.id})">Save</button>
        <div id="edit-level-error" class="alert alert-error" style="display:none;margin:0;padding:0.75rem 1rem;font-size:13px"></div>
      </div>
    </div>
  `);
}

async function saveEditSubject(subjectId) {
  const errEl = document.getElementById('edit-level-error');
  if (errEl) {
    errEl.style.display = 'none';
    errEl.textContent = '';
  }

  const name = document.getElementById('edit-level-name')?.value.trim();
  const tag = document.getElementById('edit-level-tag')?.value.trim();
  const curriculum_system = document.getElementById('edit-subject-system')?.value;
  const level_id = parseInt(document.getElementById('edit-subject-level')?.value);
  const sublevelRaw = document.getElementById('edit-subject-sublevel')?.value || '';
  const sublevel_id = sublevelRaw ? parseInt(sublevelRaw) : null;

  if (!name || !tag) {
    if (errEl) {
      errEl.textContent = 'Name and tag are required.';
      errEl.style.display = 'block';
    }
    return;
  }

  try {
    await API.put(`/api/v1/subjects/${subjectId}`, {
      name, tag, curriculum_system, level_id, sublevel_id,
    });
    closeModal();
    switchContentTab('subjects', document.querySelector('.tab-btn:nth-child(2)'));
    showNotification('Subject updated!', 'success');
  } catch (e) {
    if (errEl) {
      errEl.textContent = e.message || 'Unable to update subject.';
      errEl.style.display = 'block';
    }
  }
}

async function deleteSubject(subjectId, subjectName) {
  if (!confirm(`Delete subject "${subjectName}" and all its topics? This cannot be undone.`)) return;
  try {
    await API.delete(`/api/v1/subjects/${subjectId}`);
    switchContentTab('subjects', document.querySelector('.tab-btn:nth-child(2)'));
    showNotification('Subject deleted!', 'success');
  } catch (e) {
    showNotification(e.message || 'Unable to delete subject.', 'error');
  }
}

async function addTopic() {
  const name = document.getElementById('new-topic-name').value.trim();
  const subject_id = parseInt(document.getElementById('new-topic-subj').value);
  if (!name) return showNotification('Topic name required.', 'error');
  await API.post('/api/v1/topics', { name, subject_id });
  loadTopicsForAdmin(subject_id);
  document.getElementById('new-topic-name').value = '';
  showNotification('Topic added!', 'success');
}

async function deleteTopic(id) {
  if (!confirm('Delete this topic and all its subtopics?')) return;
  try {
    await API.delete(`/api/v1/topics/${id}`);
    const subjId = document.getElementById('new-topic-subj')?.value;
    if (subjId) loadTopicsForAdmin(subjId);
    showNotification('Topic deleted!', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to delete topic', 'error');
  }
}

async function addSubTopic() {
  const name = document.getElementById('new-st-name').value.trim();
  const topic_id = parseInt(document.getElementById('st-topic').value);
  if (!name || !topic_id) return showNotification('Name and topic required.', 'error');
  await API.post('/api/v1/subtopics', {
    name, topic_id,
    content: {
      content: document.getElementById('new-st-content').value.trim(),
      activities: document.getElementById('new-st-activities').value.trim(),
      learning_outcomes: document.getElementById('new-st-learning-outcomes').value.trim(),
      references: document.getElementById('new-st-refernces').value.trim(),
      num_lessons: parseInt(document.getElementById('new-st-lessons').value) || 2,
      key_inquiry_question: document.getElementById('new-st-kiq').value.trim(),
    },
  });
  const fb = document.getElementById('st-feedback');
  fb.textContent = `"${name}" added successfully.`;
  fb.style.display = 'flex';
  document.getElementById('new-st-name').value = '';
  setTimeout(() => fb.style.display = 'none', 3000);
}

/* ─────────────────────────────────────────────────
   Level/Subject/Topic Loaders
   ───────────────────────────────────────────────── */

async function loadLevelsForSubjectSystem() {
  const system = document.getElementById('new-subj-system')?.value;
  const levelSel = document.getElementById('new-subj-level');
  const levelSubsSel = document.getElementById('new-subj-sublevel');
  if (!levelSel || !levelSubsSel) return;

  try {
    const levelsRes = await API.get('/api/v1/levels');
    const allLevels = levelsRes.data || [];
    const filtered = allLevels.filter(l => String(l.curriculum_system) === String(system));
    const prev = parseInt(levelSel.value);

    levelSel.innerHTML = filtered.map(l => `<option value="${l.id}">${l.name}</option>`).join('') || '<option value="">No levels available</option>';

    if (filtered.some(l => l.id === prev)) {
      levelSel.value = String(prev);
    } else if (filtered.length > 0) {
      levelSel.value = String(filtered[0].id);
    }

    levelSubsSel.innerHTML = '<option value="">Select sub-level</option>';
    loadSublevelsForSubject();
  } catch (error) {
    console.error('Error loading levels:', error);
  }
}

async function loadSublevelsForSubject() {
  const levelId = parseInt(document.getElementById('new-subj-level').value);
  const subSel = document.getElementById('new-subj-sublevel');
  if (!subSel || !levelId) return;

  try {
    const levelsRes = await API.get('/api/v1/levels');
    const level = (levelsRes.data || []).find(l => String(l.id) === String(levelId));
    const subs = level?.sublevels || [];
    subSel.innerHTML = subs.map(s => `<option value="${s.id}">${s.name}</option>`).join('') || '<option value="">No sub-levels</option>';
  } catch (error) {
    console.error('Error loading sublevels:', error);
  }
}

async function loadLevelsForTopics(system) {
  const levelSel = document.getElementById('new-topic-level');
  const sublevelSel = document.getElementById('new-topic-sublevel');
  if (!levelSel || !sublevelSel) return;

  try {
    const res = await API.get('/api/v1/levels');
    const levels = res.data || [];
    const filtered = levels.filter(l => String(l.curriculum_system) === String(system));

    levelSel.innerHTML = filtered.map(l => `<option value="${l.id}">${l.name}</option>`).join('') || '<option value="">No levels</option>';
    sublevelSel.innerHTML = '<option value="">All sub-levels</option>';

    const firstLevel = filtered[0];
    if (firstLevel) await loadSublevelsForTopics(firstLevel.id);
  } catch (error) {
    console.error('Error loading levels for topics:', error);
  }
}

async function loadSublevelsForTopics(levelId) {
  const sublevelSel = document.getElementById('new-topic-sublevel');
  if (!sublevelSel) return;

  try {
    const res = await API.get('/api/v1/levels');
    const level = (res.data || []).find(l => String(l.id) === String(levelId));
    const subs = level?.sublevels || [];

    sublevelSel.innerHTML = [
      '<option value="">All sub-levels</option>',
      ...subs.map(s => `<option value="${s.id}">${s.name}</option>`),
    ].join('');

    await loadSubjectsForAdminTopics();
  } catch (error) {
    console.error('Error loading sublevels for topics:', error);
  }
}

async function loadSubjectsForAdminTopics() {
  const system = document.getElementById('new-topic-system')?.value;
  const levelId = parseInt(document.getElementById('new-topic-level')?.value);
  const sublevelIdRaw = document.getElementById('new-topic-sublevel')?.value || '';
  const sublevelId = sublevelIdRaw ? parseInt(sublevelIdRaw) : '';

  const sel = document.getElementById('new-topic-subj');
  if (!sel || !levelId) {
    sel.innerHTML = '<option value="">Select level</option>';
    return;
  }

  try {
    let url = `/api/v1/subjects?level_id=${levelId}&curriculum_system=${encodeURIComponent(system)}`;
    if (sublevelId) url += `&sublevel_id=${sublevelId}`;

    const subjRes = await API.get(url);
    const subjects = subjRes.data || [];

    sel.innerHTML = subjects.map(s => `<option value="${s.id}">${s.name}</option>`).join('') || '<option value="">No subjects</option>';

    const first = subjects[0];
    if (first) {
      loadTopicsForAdmin(first.id);
    } else {
      const c = document.getElementById('existing-topics');
      if (c) c.innerHTML = '<p class="text-muted text-sm">No subjects found for this selection.</p>';
    }
  } catch (error) {
    console.error('Error loading subjects:', error);
  }
}

async function loadTopicsForAdmin(subjId) {
  const res = await API.get(`/api/v1/topics?subject_id=${subjId}`);
  const c = document.getElementById('existing-topics');
  if (!c) return;
  c.innerHTML = `<div class="card-title" style="margin-top:.5rem">Topics (${res.data.length})</div>
    ${res.data.map(t => `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--gray-100);font-size:13px">
      <span style="flex:1">${t.name}</span>
      <span class="text-muted">${t.subtopics?.length||0} sub-topics</span>
      <button class="btn btn-sm btn-danger" onclick="deleteTopic(${t.id})">Delete</button>
    </div>`).join('') || '<p class="text-muted text-sm">No topics yet.</p>'}`;
}

async function loadLevelsForST(system) {
  const levelSel = document.getElementById('st-level');
  const sublevelSel = document.getElementById('st-sublevel');
  if (!levelSel || !sublevelSel) return;

  try {
    const res = await API.get('/api/v1/levels');
    const levels = res.data || [];
    const filtered = levels.filter(l => String(l.curriculum_system) === String(system));

    levelSel.innerHTML = filtered.map(l => `<option value="${l.id}">${l.name}</option>`).join('') || '<option value="">No levels</option>';
    sublevelSel.innerHTML = '<option value="">All sub-levels</option>';

    const firstLevel = filtered[0];
    if (firstLevel) await loadSublevelsForST(firstLevel.id);
  } catch (error) {
    console.error('Error loading levels for ST:', error);
  }
}

async function loadSublevelsForST(levelId) {
  const sublevelSel = document.getElementById('st-sublevel');
  if (!sublevelSel) return;

  try {
    const res = await API.get('/api/v1/levels');
    const level = (res.data || []).find(l => String(l.id) === String(levelId));
    const subs = level?.sublevels || [];

    sublevelSel.innerHTML = [
      '<option value="">All sub-levels</option>',
      ...subs.map(s => `<option value="${s.id}">${s.name}</option>`),
    ].join('');

    await loadSubjectsForST();
  } catch (error) {
    console.error('Error loading sublevels for ST:', error);
  }
}

async function loadSubjectsForST() {
  const system = document.getElementById('st-system')?.value;
  const levelId = parseInt(document.getElementById('st-level')?.value);
  const sublevelIdRaw = document.getElementById('st-sublevel')?.value || '';
  const sublevelId = sublevelIdRaw ? parseInt(sublevelIdRaw) : '';

  const sel = document.getElementById('st-subj');
  if (!sel || !levelId) {
    sel.innerHTML = '<option value="">Select level</option>';
    return;
  }

  try {
    let url = `/api/v1/subjects?level_id=${levelId}&curriculum_system=${encodeURIComponent(system)}`;
    if (sublevelId) url += `&sublevel_id=${sublevelId}`;

    const subjRes = await API.get(url);
    const subjects = subjRes.data || [];

    sel.innerHTML = subjects.map(s => `<option value="${s.id}">${s.name}</option>`).join('') || '<option value="">No subjects</option>';

    const first = subjects[0];
    const topicSel = document.getElementById('st-topic');
    if (first) {
      loadTopicsForST(first.id);
    } else if (topicSel) {
      topicSel.innerHTML = '<option>No topics</option>';
    }
  } catch (error) {
    console.error('Error loading subjects for ST:', error);
  }
}

async function loadTopicsForST(subjId) {
  try {
    const res = await API.get(`/api/v1/topics?subject_id=${subjId}`);
    const sel = document.getElementById('st-topic');
    if (!sel) return;
    sel.innerHTML = res.data.map(t => `<option value="${t.id}">${t.name}</option>`).join('') || '<option>No topics</option>';
  } catch (error) {
    console.error('Error loading topics for ST:', error);
  }
}

async function loadEditLevelsForSubjectSystem() {
  const system = document.getElementById('edit-subject-system')?.value;
  const levelSel = document.getElementById('edit-subject-level');
  const levelSubsSel = document.getElementById('edit-subject-sublevel');
  if (!levelSel || !levelSubsSel) return;

  try {
    const levelsRes = await API.get('/api/v1/levels');
    const allLevels = levelsRes.data || [];
    const filtered = allLevels.filter(l => String(l.curriculum_system) === String(system));
    const prev = parseInt(levelSel.value);

    levelSel.innerHTML = filtered.map(l => `<option value="${l.id}">${l.name}</option>`).join('') || '<option value="">No levels available</option>';

    if (filtered.some(l => l.id === prev)) {
      levelSel.value = String(prev);
    } else if (filtered.length > 0) {
      levelSel.value = String(filtered[0].id);
    }

    levelSubsSel.innerHTML = '<option value="">Select sub-level</option>';
    loadEditSublevelsForSubject();
  } catch (error) {
    console.error('Error loading edit levels:', error);
  }
}

async function loadEditSublevelsForSubject() {
  const levelId = parseInt(document.getElementById('edit-subject-level').value);
  const subSel = document.getElementById('edit-subject-sublevel');
  if (!subSel || !levelId) return;

  try {
    const levelsRes = await API.get('/api/v1/levels');
    const level = (levelsRes.data || []).find(l => String(l.id) === String(levelId));
    const subs = level?.sublevels || [];
    subSel.innerHTML = subs.map(s => `<option value="${s.id}">${s.name}</option>`).join('') || '<option value="">No sub-levels</option>';
  } catch (error) {
    console.error('Error loading edit sublevels:', error);
  }
}
