"""
SERVICE: Scheme of Work Generator Engine
=========================================
Generates scheme of work rows entirely from the curriculum database.
No external API calls — all logic is deterministic Python code.

Algorithm:
1. Fetch subtopics between start_subtopic and end_subtopic from the DB
2. Assign lesson numbers across teaching weeks, accounting for:
   - lessons_per_week
   - double lesson slot (counts as 2 lessons in one slot)
   - break weeks (whole or partial)
3. Build a row dict for each lesson/group of lessons per week
4. Format columns correctly for 844 or CBC system
"""
from app import db
from app.models.curriculum import Topic, SubTopic, Content
from app.models.subject import Subject


# ─── Default references per subject ──────────────────────────────
REFERENCES_844 = {
    'Physics':           ['Secondary Physics KLB Bk 3', 'Comprehensive Secondary Physics', 'Principles of Physics', 'Golden Tips Physics', "Teacher's Book"],
    'Chemistry':         ['Secondary Chemistry KLB', 'Comprehensive Chemistry', 'Chemistry for Schools', "Teacher's Book"],
    'Biology':           ['Secondary Biology KLB', 'Comprehensive Biology', 'KCSE Biology Revision', "Teacher's Book"],
    'Mathematics':       ['Secondary Mathematics KLB', 'Comprehensive Mathematics', 'KLB Mathematics Bk 3', "Teacher's Book"],
    'History & Government': ['History & Government KLB', 'KCSE History Revision', "Teacher's Book"],
    'Geography':         ['Certificate Geography', 'Geography for Schools KLB', "Teacher's Book"],
    'English':           ['Memories We Lost (Set Book)', 'Blossoms of the Savannah', 'KLB English Bk 3', "Teacher's Book"],
    'Kiswahili':         ['Kiswahili KLB', 'Fasihi ya Kiswahili', "Kitabu cha Mwalimu"],
    'CRE':               ['CRE KLB', 'Comprehensive CRE', "Teacher's Book"],
    'Science & Technology': ['Primary Science KLB', 'Comprehensive Science', "Teacher's Book"],
    'Social Studies':    ['Social Studies KLB', "Teacher's Book"],
}

REFERENCES_CBC = {
    'Mathematics':        ['MTP Mathematics Grade 7–9 T.G', 'Learners Book', 'KLB Mathematics CBC'],
    'Integrated Science': ['MTP Integrated Science Grade 7–9 T.G', 'Learners Book'],
    'Social Studies':     ['MTP Social Studies Grade 9 T.G & Learners Book'],
    'English':            ['MTP English Grade 7–9 T.G', 'Learners Book'],
    'Kiswahili':          ['MTP Kiswahili Grade 7–9 T.G', 'Kitabu cha Mwanafunzi'],
    'Creative Arts':      ['MTP Creative Arts T.G', 'Learners Book'],
}

# ─── Default learning aids per subject ───────────────────────────
AIDS_MAP = {
    'Physics':           'Charts, models, ticker-timer, spring balance, voltmeter, ammeter',
    'Chemistry':         'Test tubes, beakers, Bunsen burner, periodic table chart, chemicals',
    'Biology':           'Microscope, specimens, charts, models, hand lens',
    'Mathematics':       'Ruler, graph paper, calculator, geometrical sets, mathematical tables',
    'History & Government': 'Maps, photographs, charts, documentary films',
    'Geography':         'Maps, atlas, globe, photographs, charts',
    'English':           'Set books, dictionary, audio recordings, newspaper cuttings',
    'Kiswahili':         'Vitabu vya kiada, kamusi, vipande vya habari',
    'Science & Technology': 'Laboratory equipment, charts, models, specimens',
    'Social Studies':    'Maps, photographs, charts, newspaper cuttings',
    'Integrated Science': 'Laboratory equipment, charts, models, specimens, hand lens',
    'Creative Arts':     'Art materials, musical instruments, sports equipment',
    'CRE':               'Bible, charts, reference books',
}

# ─── Default assessment methods ──────────────────────────────────
ASSESSMENT_MAP = {
    'CBC': 'Observation, oral questions, written exercises, portfolio, project work, peer assessment',
    '844': 'Oral questions, written exercises, class tests, homework',
}


class SchemeGenerator:
    """
    Generates a full scheme of work from curriculum database content.
    Instantiate with parameters, call .generate() to get row list.
    """

    def __init__(self, subject_id: int, grade: str, term: int,
                 lessons_per_week: int, weeks: int, start_week: int,
                 double_lesson: str,
                 start_topic_id: int, start_subtopic_id: int,
                 end_topic_id: int, end_subtopic_id: int,
                 breaks: list):
        self.subject_id = subject_id
        self.grade = grade
        self.term = term
        self.lpw = max(1, lessons_per_week)
        self.weeks = max(1, weeks)
        self.start_week = max(1, start_week)
        self.double_lesson = double_lesson          # e.g. "Lesson 3 & 4" or ""
        self.start_topic_id = start_topic_id
        self.start_subtopic_id = start_subtopic_id
        self.end_topic_id = end_topic_id
        self.end_subtopic_id = end_subtopic_id
        self.breaks = breaks                       # list of {week, type, whole_week, start_lesson}

        self.subject = db.session.get(Subject, subject_id)
        self.is_cbc = self.subject.curriculum_system == 'CBC' if self.subject else False

    # ─── Public API ──────────────────────────────────────────────
    def generate(self) -> list:
        """Return a list of row dicts ready for table rendering / download."""
        subtopics = self._fetch_subtopics()
        schedule = self._build_schedule(subtopics)
        return schedule

    def references(self) -> list:
        name = self.subject.name if self.subject else ''
        if self.is_cbc:
            return REFERENCES_CBC.get(name, ['Approved CBC Textbook', "Teacher's Guide"])
        return REFERENCES_844.get(name, ['Approved KLB Textbook', "Teacher's Book"])

    # ─── Fetch ordered subtopics from DB ────────────────────────
    def _fetch_subtopics(self) -> list:
        """
        Collect all SubTopics between start_subtopic and end_subtopic
        (inclusive) by walking topics in order.
        Returns list of (topic, subtopic, content) tuples.
        """
        # Fetch all topics for this subject in order
        topics = Topic.query.filter_by(subject_id=self.subject_id)\
                            .order_by(Topic.order, Topic.id).all()

        if not topics:
            return []

        # Determine topic id range
        start_tid = self.start_topic_id or topics[0].id
        end_tid = self.end_topic_id or topics[-1].id

        # Get topic ids in order, clipped to range
        topic_ids = [t.id for t in topics]
        try:
            si = topic_ids.index(start_tid)
        except ValueError:
            si = 0
        try:
            ei = topic_ids.index(end_tid)
        except ValueError:
            ei = len(topic_ids) - 1

        selected_topics = topics[si:ei + 1]

        result = []
        for ti, topic in enumerate(selected_topics):
            sts = SubTopic.query.filter_by(topic_id=topic.id)\
                                .order_by(SubTopic.order, SubTopic.id).all()

            # Clip subtopics within first/last topic
            if ti == 0 and self.start_subtopic_id:
                st_ids = [s.id for s in sts]
                try:
                    sts = sts[st_ids.index(self.start_subtopic_id):]
                except ValueError:
                    pass

            if ti == len(selected_topics) - 1 and self.end_subtopic_id:
                st_ids = [s.id for s in sts]
                try:
                    sts = sts[:st_ids.index(self.end_subtopic_id) + 1]
                except ValueError:
                    pass

            for st in sts:
                content = Content.query.filter_by(subtopic_id=st.id).first()
                result.append((topic, st, content))

        return result

    # ─── Build week/lesson schedule ─────────────────────────────
    def _build_schedule(self, subtopics: list) -> list:
        """
        Map subtopics onto teaching weeks and lessons.
        Inserts break rows where applicable.
        Returns list of row dicts.
        """
        # Build map: week_number → break info (or None)
        break_map = {b['week']: b for b in self.breaks}

        # Effective lessons per week (double lesson adds one extra slot but same count)
        # We count lessons as slots; a double counts as 2 lessons in 1 slot
        double_slot = self._parse_double_slot()  # int or None (1-indexed lesson number)

        rows = []
        st_index = 0        # pointer into subtopics list
        total_sts = len(subtopics)

        for week_offset in range(self.weeks):
            wk = self.start_week + week_offset
            brk = break_map.get(wk)

            if brk and brk.get('whole_week'):
                rows.append(self._break_row(wk, brk['type']))
                continue

            # How many lessons are available this week?
            available = self.lpw
            if brk:
                # Partial break: lessons from start_lesson onwards are lost
                start_lsn = brk.get('start_lesson', 1)
                available = start_lsn - 1
                if available <= 0:
                    rows.append(self._break_row(wk, brk['type']))
                    continue

            # Accumulate subtopics that fit into this week's lessons
            week_sts = []
            lessons_used = 0

            while st_index < total_sts and lessons_used < available:
                topic, st, content = subtopics[st_index]
                needed = content.num_lessons if content else 1
                # Carry over if we started this subtopic in a previous week
                week_sts.append((topic, st, content, needed))
                lessons_used += needed
                st_index += 1

            if not week_sts:
                # No more content — fill with revision
                rows.append(self._revision_row(wk, available))
                continue

            # Build lesson string for this week e.g. "1-3" or "1, 2, 4"
            lsn_str = self._lesson_string(available, double_slot)

            # If multiple subtopics in one week, group them
            if len(week_sts) == 1:
                topic, st, content, _ = week_sts[0]
                rows.append(self._content_row(wk, lsn_str, topic, st, content))
            else:
                # Multiple subtopics: one row per subtopic, sharing the week number
                for idx, (topic, st, content, _) in enumerate(week_sts):
                    rows.append(self._content_row(
                        wk if idx == 0 else '',
                        '' if idx > 0 else lsn_str,
                        topic, st, content
                    ))

            # If there's a partial break this week, append the break row after content
            if brk and not brk.get('whole_week'):
                rows.append(self._partial_break_row(wk, brk['type'], brk.get('start_lesson', 1)))

        return rows

    # ─── Row builders ────────────────────────────────────────────
    def _content_row(self, wk, lsn, topic, subtopic, content) -> dict:
        subj_name = self.subject.name if self.subject else ''
        aids = AIDS_MAP.get(subj_name, 'Charts, models, textbooks')
        refs = '; '.join(self.references()[:2])
        c = content

        if self.is_cbc:
            return {
                'wk': str(wk),
                'lsn': str(lsn),
                'strand': topic.name,
                'substrand': subtopic.name,
                'outcomes': c.learning_outcomes or self._default_outcomes_cbc(subtopic.name),
                'inquiry': c.key_inquiry_question or f'What do we know about {subtopic.name}?',
                'experiences': c.activities or self._default_experiences(subtopic.name),
                'resources': (c.content or aids),
                'assessment': ASSESSMENT_MAP['CBC'],
                'refl': '',
            }
        else:
            return {
                'wk': str(wk),
                'lsn': str(lsn),
                'topic': topic.name,
                'subtopic': subtopic.name,
                'objectives': c.learning_outcomes or self._default_objectives_844(subtopic.name),
                'activities': c.activities or self._default_activities_844(subtopic.name),
                'aids': c.content or aids,
                'reference': refs,
                'remarks': '',
            }

    def _break_row(self, wk, break_type) -> dict:
        if self.is_cbc:
            return {'wk': str(wk), 'lsn': '', 'strand': '', 'substrand': f'BREAK — {break_type}',
                    'outcomes': '', 'inquiry': '', 'experiences': '', 'resources': '',
                    'assessment': '', 'refl': ''}
        return {'wk': str(wk), 'lsn': '', 'topic': 'BREAK', 'subtopic': break_type,
                'objectives': '', 'activities': '', 'aids': '', 'reference': '', 'remarks': ''}

    def _partial_break_row(self, wk, break_type, from_lesson) -> dict:
        note = f'{break_type} (from lesson {from_lesson})'
        if self.is_cbc:
            return {'wk': '', 'lsn': str(from_lesson), 'strand': '', 'substrand': f'BREAK — {note}',
                    'outcomes': '', 'inquiry': '', 'experiences': '', 'resources': '',
                    'assessment': '', 'refl': ''}
        return {'wk': '', 'lsn': str(from_lesson), 'topic': 'BREAK', 'subtopic': note,
                'objectives': '', 'activities': '', 'aids': '', 'reference': '', 'remarks': ''}

    def _revision_row(self, wk, available) -> dict:
        lsn = self._lesson_string(available, self._parse_double_slot())
        if self.is_cbc:
            return {'wk': str(wk), 'lsn': lsn, 'strand': 'Revision', 'substrand': 'End of term revision',
                    'outcomes': 'Learner consolidates all strands covered in the term.',
                    'inquiry': 'What have we learnt this term?',
                    'experiences': 'Revision exercises, past paper questions, group discussion.',
                    'resources': 'Learner\'s book, past papers', 'assessment': ASSESSMENT_MAP['CBC'], 'refl': ''}
        return {'wk': str(wk), 'lsn': lsn, 'topic': 'Revision', 'subtopic': 'End of term revision',
                'objectives': 'By end of lesson learner should be able to revise all topics covered.',
                'activities': 'Answering past paper questions, class discussion, practice exercises.',
                'aids': 'Past papers, textbooks', 'reference': '', 'remarks': ''}

    # ─── Lesson string helper ─────────────────────────────────────
    def _parse_double_slot(self):
        """Return 1-indexed lesson number for double slot, or None."""
        if not self.double_lesson:
            return None
        import re
        m = re.search(r'(\d+)', self.double_lesson)
        return int(m.group(1)) if m else None

    def _lesson_string(self, available_lessons: int, double_slot) -> str:
        """Build a string like '1-5' or '1-4' representing lessons for the week."""
        if available_lessons <= 0:
            return ''
        return f'1-{available_lessons}'

    # ─── Default text generators (rule-based) ────────────────────
    def _default_objectives_844(self, subtopic: str) -> str:
        return (
            f'By the end of the lesson the learner should be able to:\n'
            f'(a) Define {subtopic.lower()}.\n'
            f'(b) Explain the concept of {subtopic.lower()}.\n'
            f'(c) Solve problems related to {subtopic.lower()}.'
        )

    def _default_outcomes_cbc(self, substrand: str) -> str:
        return (
            f'By the end of the lesson, the learner should be able to:\n'
            f'(a) Describe {substrand.lower()}.\n'
            f'(b) Demonstrate understanding of {substrand.lower()} through activities.\n'
            f'(c) Apply knowledge of {substrand.lower()} in real-life situations.'
        )

    def _default_activities_844(self, subtopic: str) -> str:
        return (
            f'• Teacher introduces {subtopic.lower()} using aids.\n'
            f'• Learners discuss and take notes.\n'
            f'• Worked examples solved on board.\n'
            f'• Learners practise exercise questions.\n'
            f'• Class discussion and correction.'
        )

    def _default_experiences(self, substrand: str) -> str:
        return (
            f'• Learner is guided to explore {substrand.lower()}.\n'
            f'• Learner discusses with peers in groups.\n'
            f'• Learner makes observations and records findings.\n'
            f'• Learner presents findings to the class.'
        )
