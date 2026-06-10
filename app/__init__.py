"""
SchemePro — Flask Application Factory
MVC Pattern:
  Models      → app/models/
  Controllers → app/controllers/
  Views       → app/templates/
  Service     → app/services/scheme_engine.py  (no external API)
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app(config=None):
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///schemepro.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config:
        app.config.update(config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r'/api/*': {'origins': '*'}})
    login_manager.login_view = 'auth.login'

    from app.models import User, SchemeDraft

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.controllers.auth_controller import auth_bp
    from app.controllers.main_controller import main_bp
    from app.controllers.api_controller import api_bp
    from app.controllers.admin_controller import admin_bp
    from app.controllers.scheme_controller import scheme_bp
    from app.controllers.wallet_controller import wallet_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(admin_bp, url_prefix='/admin-panel')
    app.register_blueprint(scheme_bp, url_prefix='/scheme')
    app.register_blueprint(wallet_bp, url_prefix='/wallet')

    with app.app_context():
        db.create_all()
        try:
            _seed_initial_data()
        except OperationalError:
            # DB schema is not yet migrated; skip seeding until migrations are applied.
            pass

    return app


# ─────────────────────────────────────────────────────────────────
# SEED DATA
# Full KICD-aligned curriculum content — no external API needed
# ─────────────────────────────────────────────────────────────────
def _seed_initial_data():
    from app.models.role import Role
    # FIX: Imported the CurriculumSystem model
    from app.models.level import Level, SubLevel, CurriculumSystem
    from app.models.subject import Subject
    from app.models.curriculum import Topic, SubTopic, Content
    from app.models.user import User
    from app.models.pricing import DocumentPricing

    # ── Roles ──────────────────────────────────────────────────────
    if not Role.query.first():
        db.session.add_all([
            Role(tag='superuser', name='Super Administrator'),
            Role(tag='admin',     name='Administrator'),
            Role(tag='support',   name='Support Staff'),
            Role(tag='client',    name='Client / Teacher'),
        ])
        db.session.commit()

    # ── FIX: Seed Curriculum Systems First ──────────────────────────
    if not CurriculumSystem.query.first():
        db.session.add_all([
            CurriculumSystem(name="8-4-4 System", tag="844"),
            CurriculumSystem(name="Competency Based Curriculum", tag="CBC")
        ])
        db.session.commit()

    # ── Levels & SubLevels ─────────────────────────────────────────
    if not Level.query.first():
        levels_data = [
            ('Upper Primary', 'upper_primary', '844',
             [('std4','Std 4'),('std5','Std 5'),('std6','Std 6'),
              ('std7','Std 7'),('std8','Std 8')]),
            ('Junior School (CBC)', 'junior_cbc', 'CBC',
             [('grade7','Grade 7'),('grade8','Grade 8'),('grade9','Grade 9')]),
            ('Senior School', 'senior', '844',
             [('form1','Form 1'),('form2','Form 2'),
              ('form3','Form 3'),('form4','Form 4')]),
        ]
        for name, tag, system_tag, sls in levels_data:
            # FIX: Look up the real database object instance using the tag
            system_obj = CurriculumSystem.query.filter_by(tag=system_tag).first()
            
            lvl = Level(name=name, tag=tag, curriculum_system=system_obj)
            db.session.add(lvl)
            db.session.flush()
            for sl_tag, sl_name in sls:
                db.session.add(SubLevel(name=sl_name, tag=sl_tag, level_id=lvl.id))
        db.session.commit()

    # ── Subjects ────────────────────────────────────────────────────
    if not Subject.query.first():
        upper = Level.query.filter_by(tag='upper_primary').first()
        junior = Level.query.filter_by(tag='junior_cbc').first()
        senior = Level.query.filter_by(tag='senior').first()

        subjects_map = [
            # (tag, name, level_obj, system)
            ('math_primary',    'Mathematics',          upper,  '844'),
            ('english_primary', 'English',              upper,  '844'),
            ('kisw_primary',    'Kiswahili',            upper,  '844'),
            ('sci_primary',     'Science & Technology', upper,  '844'),
            ('social_primary',  'Social Studies',       upper,  '844'),
            ('cre_primary',     'CRE / IRE',            upper,  '844'),
            ('math_junior',     'Mathematics',          junior, 'CBC'),
            ('sci_junior',      'Integrated Science',   junior, 'CBC'),
            ('social_junior',   'Social Studies',       junior, 'CBC'),
            ('eng_junior',      'English',              junior, 'CBC'),
            ('kisw_junior',     'Kiswahili',            junior, 'CBC'),
            ('arts_junior',     'Creative Arts',        junior, 'CBC'),
            ('physics_senior',  'Physics',              senior, '844'),
            ('chem_senior',     'Chemistry',            senior, '844'),
            ('bio_senior',      'Biology',              senior, '844'),
            ('math_senior',     'Mathematics',          senior, '844'),
            ('hist_senior',     'History & Government', senior, '844'),
            ('geo_senior',      'Geography',            senior, '844'),
            ('eng_senior',      'English',              senior, '844'),
            ('cre_senior',      'CRE',                  senior, '844'),
        ]
        for tag, name, lvl, sys in subjects_map:
            if lvl:
                db.session.add(Subject(tag=tag, name=name,
                                       level_id=lvl.id, curriculum_system=sys))
        db.session.commit()

    # ── Curriculum content (seed once) ──────────────────────────────
    if not Topic.query.first():
        _seed_curriculum()

    # ── Document pricing ─────────────────────────────────────────────
    if not DocumentPricing.query.first():
        db.session.add_all([
            DocumentPricing(doc_type='pdf',  label='PDF Document',           price=30.0),
            DocumentPricing(doc_type='docx', label='Word Document (.docx)',   price=50.0),
            DocumentPricing(doc_type='zip',  label='ZIP Bundle (PDF + DOCX)', price=70.0),
        ])
        db.session.commit()

    # ── Superuser ─────────────────────────────────────────────────────
    su_role = Role.query.filter_by(tag='superuser').first()
    if su_role and not User.query.filter_by(username='admin').first():
        from app import bcrypt as _bcrypt
        pw = _bcrypt.generate_password_hash('Admin@1234').decode('utf-8')
        u = User(name='System Administrator', username='admin',
                 email='admin@schemepro.co.ke', password=pw, role_id=su_role.id)
        db.session.add(u)
        db.session.flush()
        from app.models.wallet import Wallet
        db.session.add(Wallet(user_id=u.id, balance=500.0))
        db.session.commit()


def _seed_curriculum():
    """
    Seed rich KICD-aligned curriculum content for all subjects.
    Content is stored in the DB; SchemeGenerator reads it at runtime.
    No AI API involved — all content is written directly here.
    """
    from app.models.subject import Subject
    from app.models.curriculum import Topic, SubTopic, Content

    def add_topic(subj_tag, topic_name, subtopics, order=0):
        """
        subtopics: list of (name, aids, num_lessons, kiq, outcomes, activities, refs)
        """
        subj = Subject.query.filter_by(tag=subj_tag).first()
        if not subj:
            return
        t = Topic(name=topic_name, subject_id=subj.id, order=order)
        db.session.add(t)
        db.session.flush()
        for idx, st_data in enumerate(subtopics):
            st_name, aids, num_lsn, kiq, outcomes, activities, refs = st_data
            st = SubTopic(name=st_name, topic_id=t.id, order=idx)
            db.session.add(st)
            db.session.flush()
            db.session.add(Content(
                subtopic_id=st.id,
                content=aids,
                num_lessons=num_lsn,
                key_inquiry_question=kiq,
                learning_outcomes=outcomes,
                activities=activities,
                references=refs,
            ))
        db.session.commit()

    # ════════════════════════════════════════════════════════════
    # PHYSICS (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('physics_senior', 'Measurements and Practical Skills', [
        ('Estimating and Measuring Length',
         'Ruler, metre rule, Vernier calipers, micrometer screw gauge', 3,
         'How do scientists ensure accurate and precise measurements?',
         'By end of lesson learner should be able to:\n(a) Estimate lengths using appropriate instruments.\n(b) Use Vernier calipers and micrometer screw gauge accurately.\n(c) State the SI unit of length.',
         '• Teacher demonstrates use of measuring instruments.\n• Learners practice reading Vernier calipers.\n• Learners measure objects and record results.\n• Class discussion on sources of error.',
         'Secondary Physics KLB Bk 1 pp 1-15; Comprehensive Physics pp 3-10'),
        ('Mass, Weight and Density',
         'Electronic balance, spring balance, beam balance, various objects', 3,
         'What is the difference between mass and weight?',
         'By end of lesson learner should be able to:\n(a) Define mass, weight and density.\n(b) Distinguish between mass and weight.\n(c) Calculate density of regular and irregular objects.',
         '• Teacher explains concepts of mass, weight and density.\n• Learners measure mass using a balance.\n• Learners calculate density of regular objects.\n• Problem solving exercises on density.',
         'Secondary Physics KLB Bk 1 pp 16-28; Comprehensive Physics pp 11-18'),
        ('Volume Measurement',
         'Measuring cylinder, burette, pipette, irregular solids, water', 2,
         'How do we measure the volume of irregular objects?',
         'By end of lesson learner should be able to:\n(a) Measure volume of liquids using appropriate apparatus.\n(b) Determine volume of irregular solids by displacement method.\n(c) Apply knowledge to solve problems.',
         '• Learners measure volumes of liquids using measuring cylinders.\n• Learners find volume of irregular objects by displacement.\n• Recording and presenting data in tables.',
         'Secondary Physics KLB Bk 1 pp 29-35'),
    ], order=1)

    add_topic('physics_senior', 'Linear Motion', [
        ('Distance, Displacement, Speed and Velocity',
         'Ticker-timer, tape, trolley, stopwatch, measuring tape', 4,
         'How do we accurately describe and measure motion?',
         'By end of lesson learner should be able to:\n(a) Define distance, displacement, speed and velocity.\n(b) Distinguish between scalar and vector quantities.\n(c) Use ticker-timer to determine velocity.',
         '• Teacher defines and distinguishes distance from displacement.\n• Learners use ticker-timer to find velocity.\n• Learners plot distance-time graphs.\n• Problem solving on speed and velocity.',
         'Secondary Physics KLB Bk 1 pp 40-55; Comprehensive Physics pp 25-35'),
        ('Acceleration and Deceleration',
         'Trolley, inclined plane, ticker-timer, tape, weights', 4,
         'What causes a change in the velocity of a moving object?',
         'By end of lesson learner should be able to:\n(a) Define acceleration and deceleration.\n(b) Calculate acceleration from velocity-time graphs.\n(c) Use equations of motion to solve problems.',
         '• Demonstration of accelerating trolley on inclined plane.\n• Learners plot velocity-time graphs from ticker-tape results.\n• Learners derive and apply equations of linear motion.\n• Worked examples and practice problems.',
         'Secondary Physics KLB Bk 1 pp 56-70'),
        ('Relative Motion',
         'Charts, videos showing relative motion scenarios', 2,
         'How does the observer\'s frame of reference affect perceived motion?',
         'By end of lesson learner should be able to:\n(a) Define relative motion.\n(b) Solve problems involving relative motion of two objects.\n(c) Apply relative motion concepts to real-life situations.',
         '• Teacher explains relative motion using examples.\n• Learners solve numerical problems on relative motion.\n• Discussion of real-life examples.',
         'Secondary Physics KLB Bk 1 pp 71-78'),
    ], order=2)

    add_topic('physics_senior', "Newton's Laws of Motion", [
        ("Newton's First Law — Inertia",
         'Smooth surface, marbles, coin-and-card demonstration, coin stacking', 2,
         'Why do objects resist changes to their state of motion?',
         'By end of lesson learner should be able to:\n(a) State Newton\'s First Law of Motion.\n(b) Define inertia.\n(c) Give practical examples of inertia in daily life.',
         '• Demonstration of inertia using coin-and-card experiment.\n• Class discussion on everyday examples of Newton\'s First Law.\n• Learners write explanations for given inertia examples.',
         'Secondary Physics KLB Bk 1 pp 82-88'),
        ("Newton's Second Law — Force and Acceleration",
         'Trolley, spring balance, weights, ticker-timer, smooth track', 4,
         'How does the net force on an object relate to its acceleration?',
         'By end of lesson learner should be able to:\n(a) State Newton\'s Second Law of Motion.\n(b) Define the newton as a unit of force.\n(c) Solve problems using F = ma.',
         '• Experiment: varying force and mass on trolley, measuring acceleration.\n• Learners plot force-acceleration and mass-acceleration graphs.\n• Deriving F = ma from experimental results.\n• Problem solving using F = ma.',
         'Secondary Physics KLB Bk 1 pp 89-100'),
        ("Newton's Third Law — Action and Reaction",
         'Balloon, trolley, spring balance pairs, Newton\'s cradle (if available)', 2,
         'Why do action and reaction forces not cancel each other out?',
         'By end of lesson learner should be able to:\n(a) State Newton\'s Third Law.\n(b) Identify action-reaction pairs in given situations.\n(c) Explain why action-reaction pairs do not cancel.',
         '• Balloon rocket demonstration.\n• Discussion of rocket propulsion, swimming, walking.\n• Learners identify action-reaction pairs in pictures.\n• Problem solving.',
         'Secondary Physics KLB Bk 1 pp 101-108'),
    ], order=3)

    add_topic('physics_senior', 'Work, Energy and Power', [
        ('Work Done by a Force',
         'Spring balance, ruler, inclined plane, weights', 3,
         'When is work done in the scientific sense?',
         'By end of lesson learner should be able to:\n(a) Define work in scientific terms.\n(b) Calculate work done by a constant force.\n(c) State the SI unit of work (joule).',
         '• Teacher explains scientific definition of work vs everyday meaning.\n• Learners calculate work done in various scenarios.\n• Concept of positive, negative and zero work.\n• Practice problems.',
         'Secondary Physics KLB Bk 2 pp 1-12'),
        ('Kinetic and Potential Energy',
         'Pendulum, ball, ramp, spring, rubber band', 4,
         'How is energy transformed from one form to another?',
         'By end of lesson learner should be able to:\n(a) Define kinetic and potential energy.\n(b) Derive formulae KE = ½mv² and PE = mgh.\n(c) Apply the law of conservation of energy.',
         '• Pendulum demonstration of energy transformation.\n• Learners calculate KE and PE for given objects.\n• Discussion of energy conservation.\n• Problem solving on energy transformation.',
         'Secondary Physics KLB Bk 2 pp 13-25'),
        ('Power and Machines',
         'Pulley system, inclined plane, lever, wheel-and-axle', 4,
         'How do simple machines make work easier?',
         'By end of lesson learner should be able to:\n(a) Define power and state its SI unit (watt).\n(b) Calculate power in given situations.\n(c) Define and calculate mechanical advantage, velocity ratio and efficiency.',
         '• Demonstration of simple machines.\n• Learners measure MA and VR of pulley systems.\n• Calculation of efficiency of machines.\n• Problem solving on power and machines.',
         'Secondary Physics KLB Bk 2 pp 26-45'),
    ], order=4)

    add_topic('physics_senior', 'Waves', [
        ('Production and Properties of Waves',
         'Slinky spring, ripple tank, rope', 3,
         'What are the properties common to all waves?',
         'By end of lesson learner should be able to:\n(a) Define a wave and identify types of waves.\n(b) Define amplitude, wavelength, frequency and period.\n(c) State and use the wave equation v = fλ.',
         '• Demonstration of waves using slinky spring.\n• Learners identify transverse and longitudinal waves.\n• Learners use the wave equation to solve problems.',
         'Secondary Physics KLB Bk 2 pp 50-65'),
        ('Sound Waves',
         'Tuning forks, resonance tube, sounding board, bell jar and vacuum pump', 3,
         'How is sound produced and transmitted?',
         'By end of lesson learner should be able to:\n(a) Describe how sound is produced and transmitted.\n(b) Explain the properties of sound waves.\n(c) Describe echoes and their applications.',
         '• Tuning fork experiments on sound production.\n• Bell jar experiment on sound transmission through vacuum.\n• Discussion of applications of echoes (sonar, ultrasound).',
         'Secondary Physics KLB Bk 2 pp 66-80'),
    ], order=5)

    # ════════════════════════════════════════════════════════════
    # CHEMISTRY (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('chem_senior', 'Introduction to Chemistry', [
        ('Laboratory Safety and Apparatus',
         'Beakers, flasks, test tubes, Bunsen burner, safety charts, MSDS sheets', 2,
         'How do we ensure safety when working in a chemistry laboratory?',
         'By end of lesson learner should be able to:\n(a) State safety rules in the chemistry laboratory.\n(b) Identify common laboratory apparatus and their uses.\n(c) Demonstrate proper use and storage of apparatus.',
         '• Teacher introduces laboratory safety rules.\n• Learners identify and name common apparatus.\n• Demonstration of safe handling of chemicals.\n• Learners draw and label common apparatus.',
         'Secondary Chemistry KLB Bk 1 pp 1-15'),
        ('Separation of Mixtures',
         'Filtration apparatus, evaporating dish, distillation flask, chromatography paper, solvents', 4,
         'How can we separate the components of a mixture?',
         'By end of lesson learner should be able to:\n(a) Define a mixture and a pure substance.\n(b) Describe methods of separating mixtures.\n(c) Identify appropriate separation methods for given mixtures.',
         '• Practical: filtration of soil-water mixture.\n• Practical: simple distillation of salty water.\n• Practical: paper chromatography of ink.\n• Discussion of industrial applications.',
         'Secondary Chemistry KLB Bk 1 pp 16-40'),
    ], order=1)

    add_topic('chem_senior', 'Acids, Bases and Salts', [
        ('Properties of Acids and Bases',
         'Litmus paper, universal indicator, pH meter, common acids and bases, fruits', 3,
         'How do acids and bases affect living organisms and the environment?',
         'By end of lesson learner should be able to:\n(a) Define acids and bases using Arrhenius and Brønsted-Lowry theories.\n(b) List physical and chemical properties of acids and bases.\n(c) Use indicators to test for acids and bases.',
         '• Learners test various substances with indicators.\n• Comparison of properties of strong and weak acids.\n• Discussion of everyday acids and bases.',
         'Secondary Chemistry KLB Bk 2 pp 1-20'),
        ('Neutralisation and Salts',
         'Burette, pipette, conical flask, sodium hydroxide, hydrochloric acid, phenolphthalein', 4,
         'What happens when an acid reacts with a base?',
         'By end of lesson learner should be able to:\n(a) Define neutralisation.\n(b) Write equations for neutralisation reactions.\n(c) Perform a simple titration to determine concentration.',
         '• Practical: acid-base titration.\n• Learners prepare a salt by neutralisation.\n• Writing ionic equations for neutralisation.\n• Problem solving on titration calculations.',
         'Secondary Chemistry KLB Bk 2 pp 21-45'),
        ('Preparation and Uses of Salts',
         'Evaporating dish, filter funnel, various reactants for salt preparation', 4,
         'How are salts prepared and what are their uses?',
         'By end of lesson learner should be able to:\n(a) Describe methods of preparing soluble and insoluble salts.\n(b) Write equations for salt preparation reactions.\n(c) State uses of common salts.',
         '• Practical: preparation of copper(II) sulphate crystals.\n• Practical: preparation of barium sulphate (insoluble salt).\n• Discussion of industrial importance of salts.',
         'Secondary Chemistry KLB Bk 2 pp 46-65'),
    ], order=2)

    add_topic('chem_senior', 'Carbon and its Compounds', [
        ('Allotropes of Carbon',
         'Diamond and graphite samples (or models), charts showing crystal structures', 2,
         'Why do allotropes of the same element have different physical properties?',
         'By end of lesson learner should be able to:\n(a) Define allotropy.\n(b) Describe the structure and properties of diamond and graphite.\n(c) Explain differences in properties based on structure.',
         '• Teacher shows samples/models of diamond and graphite.\n• Learners compare properties and uses.\n• Discussion of fullerenes and their applications.',
         'Secondary Chemistry KLB Bk 3 pp 1-15'),
        ('Organic Chemistry — Alkanes',
         'Molecular models, charts of homologous series', 4,
         'What is the basis of organic chemistry?',
         'By end of lesson learner should be able to:\n(a) Define organic chemistry and carbon compounds.\n(b) Write structural and molecular formulae of alkanes.\n(c) State physical and chemical properties of alkanes.',
         '• Introduction to carbon bonding and organic molecules.\n• Learners build molecular models of alkanes.\n• Discussion of properties and uses of alkanes (LPG, petrol).',
         'Secondary Chemistry KLB Bk 3 pp 16-40'),
    ], order=3)

    # ════════════════════════════════════════════════════════════
    # BIOLOGY (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('bio_senior', 'Cell Biology', [
        ('Cell Structure and Organisation',
         'Microscope, prepared slides (animal and plant cells), charts of cell structure', 3,
         'What are the basic structural and functional units of living organisms?',
         'By end of lesson learner should be able to:\n(a) Describe the structure of animal and plant cells.\n(b) State the functions of cell organelles.\n(c) Distinguish between prokaryotic and eukaryotic cells.',
         '• Teacher introduces the cell theory.\n• Learners observe cells under microscope.\n• Drawing and labelling animal and plant cells.\n• Comparing prokaryotic and eukaryotic cells.',
         'Secondary Biology KLB Bk 1 pp 1-25'),
        ('Cell Division — Mitosis',
         'Microscope, slides of onion root tip, charts showing stages of mitosis', 3,
         'How do cells reproduce to enable growth and repair of tissues?',
         'By end of lesson learner should be able to:\n(a) Define mitosis.\n(b) Describe the stages of mitosis.\n(c) State the significance of mitosis.',
         '• Teacher explains the stages of mitosis.\n• Learners observe and draw stages using slides.\n• Discussion of significance in growth and healing.',
         'Secondary Biology KLB Bk 1 pp 26-42'),
    ], order=1)

    add_topic('bio_senior', 'Nutrition', [
        ('Nutrition in Plants — Photosynthesis',
         'Green plants, potted plants, iodine solution, ethanol, water bath, charts', 4,
         'How do green plants manufacture their own food?',
         'By end of lesson learner should be able to:\n(a) Define photosynthesis and write the overall equation.\n(b) Describe the light-dependent and light-independent reactions.\n(c) State factors affecting the rate of photosynthesis.',
         '• Experiment to show starch production in leaves.\n• Experiment to show oxygen is produced in photosynthesis.\n• Discussion of factors affecting photosynthesis rate.\n• Problem solving on photosynthesis.',
         'Secondary Biology KLB Bk 1 pp 50-75'),
        ('Nutrition in Animals — Digestion',
         'Charts of digestive system, models of digestive system, enzyme solutions', 4,
         'How do animals obtain nutrients from food?',
         'By end of lesson learner should be able to:\n(a) Describe physical and chemical digestion.\n(b) State the role of enzymes in digestion.\n(c) Trace the digestion of a meal through the alimentary canal.',
         '• Teacher explains the digestive system using charts/models.\n• Practical: testing food substances for starch, protein, sugars, fats.\n• Discussion of absorption and assimilation.',
         'Secondary Biology KLB Bk 1 pp 76-110'),
    ], order=2)

    add_topic('bio_senior', 'Transport in Animals and Plants', [
        ('Transport in Plants — Osmosis and Diffusion',
         'Osmosis experiment materials: potato cylinders, salt solutions, measuring ruler', 3,
         'How do substances move in and out of cells?',
         'By end of lesson learner should be able to:\n(a) Define diffusion, osmosis and active transport.\n(b) Demonstrate osmosis using potato experiment.\n(c) Explain the role of osmosis in plant cells.',
         '• Practical: osmosis in potato cylinders.\n• Discussion of turgor, plasmolysis and flaccidity.\n• Application to real-life situations.',
         'Secondary Biology KLB Bk 2 pp 1-20'),
        ('Blood and the Circulatory System',
         'Charts of heart and circulatory system, microscope slides of blood smears', 4,
         'How does the circulatory system transport materials around the body?',
         'By end of lesson learner should be able to:\n(a) Describe the composition of blood.\n(b) Describe the structure and function of the heart.\n(c) Trace the path of blood through the double circulatory system.',
         '• Teacher explains structure of the heart.\n• Learners observe blood smears under microscope.\n• Drawing and labelling the heart.\n• Tracing blood flow through the body.',
         'Secondary Biology KLB Bk 2 pp 21-55'),
    ], order=3)

    # ════════════════════════════════════════════════════════════
    # MATHEMATICS (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('math_senior', 'Quadratic Expressions and Equations', [
        ('Factorisation of Quadratic Expressions',
         'Mathematical tables, graph paper, calculator', 3,
         'How do we simplify and solve quadratic expressions?',
         'By end of lesson learner should be able to:\n(a) Factorise quadratic expressions of the form ax² + bx + c.\n(b) Identify perfect squares and difference of two squares.\n(c) Apply factorisation to solve problems.',
         '• Teacher demonstrates factorisation by inspection and grouping.\n• Learners practise factorising various quadratic expressions.\n• Problem solving in pairs.',
         'Secondary Mathematics KLB Bk 3 pp 1-18'),
        ('Solving Quadratic Equations',
         'Calculator, graph paper, mathematical tables', 4,
         'What methods can we use to solve quadratic equations?',
         'By end of lesson learner should be able to:\n(a) Solve quadratic equations by factorisation.\n(b) Solve quadratic equations by completing the square.\n(c) Use the quadratic formula to solve equations.',
         '• Teacher explains three methods of solving quadratic equations.\n• Learners apply each method to worked examples.\n• Learners identify when each method is most appropriate.\n• Practice exercise.',
         'Secondary Mathematics KLB Bk 3 pp 19-35'),
        ('Graphs of Quadratic Functions',
         'Graph paper, ruler, pencil, calculator', 3,
         'What does the graph of a quadratic function look like and what does it tell us?',
         'By end of lesson learner should be able to:\n(a) Draw graphs of quadratic functions.\n(b) Read roots from a quadratic graph.\n(c) Identify vertex, axis of symmetry and y-intercept.',
         '• Learners complete tables of values for quadratic functions.\n• Learners draw graphs and identify key features.\n• Using graphs to solve quadratic equations.',
         'Secondary Mathematics KLB Bk 3 pp 36-50'),
    ], order=1)

    add_topic('math_senior', 'Approximations and Errors', [
        ('Rounding and Significant Figures',
         'Calculator, number charts', 2,
         'Why is it important to round numbers appropriately?',
         'By end of lesson learner should be able to:\n(a) Round off numbers to specified decimal places.\n(b) Express numbers to given significant figures.\n(c) State the importance of significant figures in measurements.',
         '• Teacher explains rounding rules.\n• Learners round numbers to specified dp and sf.\n• Discussion of real-life applications.',
         'Secondary Mathematics KLB Bk 3 pp 55-65'),
        ('Absolute and Relative Errors',
         'Measuring instruments, calculator', 3,
         'What is the difference between absolute and relative error?',
         'By end of lesson learner should be able to:\n(a) Define absolute error, relative error and percentage error.\n(b) Calculate errors in measurements and computations.\n(c) Propagate errors in sums, differences, products and quotients.',
         '• Teacher defines types of errors.\n• Learners calculate errors in various measurements.\n• Problem solving on error propagation.',
         'Secondary Mathematics KLB Bk 3 pp 66-80'),
    ], order=2)

    add_topic('math_senior', 'Trigonometry', [
        ('Trigonometric Ratios',
         'Protractor, ruler, graph paper, scientific calculator', 4,
         'How do we use angles and sides in right-angled triangles to solve problems?',
         'By end of lesson learner should be able to:\n(a) Define sine, cosine and tangent ratios.\n(b) Use trigonometric tables and calculators to find ratios.\n(c) Solve right-angled triangles using trigonometric ratios.',
         '• Teacher introduces SOH-CAH-TOA.\n• Learners use tables and calculators to find trig ratios.\n• Worked examples on finding angles and sides.\n• Practical: measuring heights using clinometers.',
         'Secondary Mathematics KLB Bk 3 pp 85-110'),
        ('Trigonometric Graphs',
         'Graph paper, scientific calculator, ruler', 3,
         'What are the key features of trigonometric graphs?',
         'By end of lesson learner should be able to:\n(a) Draw graphs of y = sin x, y = cos x and y = tan x.\n(b) Identify period, amplitude and range.\n(c) Use graphs to solve trigonometric equations.',
         '• Learners complete tables of values for trig functions.\n• Learners draw and compare trig graphs.\n• Reading solutions from graphs.',
         'Secondary Mathematics KLB Bk 3 pp 111-130'),
    ], order=3)

    # ════════════════════════════════════════════════════════════
    # HISTORY & GOVERNMENT (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('hist_senior', 'Evolution of Man and Development of Agriculture', [
        ('Evolution of Man',
         'Charts showing stages of evolution, photographs of early man, atlas', 3,
         'How did early humans evolve and spread across the world?',
         'By end of lesson learner should be able to:\n(a) Describe the evolution of man from Homo habilis to Homo sapiens.\n(b) Identify sites where early man fossils have been found in Africa.\n(c) Explain the significance of upright posture and brain development.',
         '• Teacher presents fossil evidence and evolutionary tree.\n• Learners study maps of early man migration routes.\n• Discussion of Kenya\'s role as cradle of humankind.\n• Timeline activity.',
         'History & Government KLB Bk 1 pp 1-20'),
        ('Development of Agriculture',
         'Pictures and charts of early farming, maps of agricultural development', 3,
         'How did the discovery of agriculture transform human societies?',
         'By end of lesson learner should be able to:\n(a) Describe the Neolithic Revolution.\n(b) Explain the shift from hunting-gathering to farming.\n(c) Assess the impact of agriculture on human settlement.',
         '• Discussion of Neolithic Revolution evidence.\n• Learners compare hunter-gatherer and farming lifestyles.\n• Map work on spread of agriculture.',
         'History & Government KLB Bk 1 pp 21-40'),
    ], order=1)

    add_topic('hist_senior', 'Contacts Between Africa and the Outside World', [
        ('The Trans-Saharan Trade',
         'Maps of trans-Saharan routes, photographs, charts', 3,
         'What was the significance of the trans-Saharan trade to African societies?',
         'By end of lesson learner should be able to:\n(a) Describe the routes of the trans-Saharan trade.\n(b) Identify the items traded.\n(c) Assess the impact of the trade on North and West Africa.',
         '• Map work on trans-Saharan routes.\n• Discussion of traded commodities (gold, salt, slaves).\n• Impact assessment activity.',
         'History & Government KLB Bk 2 pp 1-22'),
        ('The East African Coast and the Indian Ocean Trade',
         'Maps of East African coast, photographs of Swahili architecture, charts', 3,
         'How did Indian Ocean trade transform the East African coast?',
         'By end of lesson learner should be able to:\n(a) Describe the Indian Ocean trade network.\n(b) Explain the development of the Swahili civilisation.\n(c) Assess the impact of the trade on East Africa.',
         '• Map work on Indian Ocean trade routes.\n• Discussion of Swahili city-states.\n• Analysis of archaeological evidence.',
         'History & Government KLB Bk 2 pp 23-48'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # GEOGRAPHY (Senior, 844)
    # ════════════════════════════════════════════════════════════
    add_topic('geo_senior', 'The Earth and the Solar System', [
        ('The Solar System',
         'Globe, orrery model, charts of solar system, atlas', 2,
         'What is the position of the Earth in the solar system?',
         'By end of lesson learner should be able to:\n(a) Describe the solar system.\n(b) State the positions of planets relative to the sun.\n(c) Explain the effects of the Earth\'s rotation and revolution.',
         '• Teacher presents solar system model.\n• Learners label diagram of solar system.\n• Discussion of seasons and day/night.',
         'Certificate Geography Bk 1 pp 1-15'),
        ('The Structure of the Earth',
         'Cross-section charts of Earth\'s interior, seismograph diagrams', 2,
         'What lies beneath the Earth\'s surface?',
         'By end of lesson learner should be able to:\n(a) Describe the internal structure of the Earth.\n(b) Explain evidence used to study Earth\'s interior.\n(c) Define the terms crust, mantle and core.',
         '• Teacher explains layers using cross-section chart.\n• Discussion of seismological evidence.\n• Learners draw and label Earth\'s cross-section.',
         'Certificate Geography Bk 1 pp 16-30'),
    ], order=1)

    add_topic('geo_senior', 'Volcanicity', [
        ('Types of Volcanoes',
         'Charts and photographs of different volcanoes, maps showing volcano locations', 3,
         'What causes volcanic eruptions and where do they occur?',
         'By end of lesson learner should be able to:\n(a) Define volcanicity.\n(b) Describe types of volcanoes and volcanic features.\n(c) Locate major volcanic regions on a world map.',
         '• Teacher presents types of volcanoes with photographs.\n• Map work on volcanic zones.\n• Discussion of causes of volcanic eruptions.',
         'Certificate Geography Bk 1 pp 35-55'),
        ('Effects and Significance of Volcanicity',
         'Case study materials, photographs, newspaper cuttings', 3,
         'What are the positive and negative effects of volcanic activity?',
         'By end of lesson learner should be able to:\n(a) Describe the effects of volcanic eruptions.\n(b) Assess the positive benefits of volcanicity.\n(c) Discuss volcanic activity in Kenya (Mt Kenya, Mt Longonot).',
         '• Case study of a volcanic eruption.\n• Discussion of positive effects (fertile soils, tourism, minerals).\n• Kenyan volcanoes field study preparation.',
         'Certificate Geography Bk 1 pp 56-70'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # MATHEMATICS — Junior (CBC, Grade 7-9)
    # ════════════════════════════════════════════════════════════
    add_topic('math_junior', 'Numbers', [
        ('Whole Numbers and Place Value',
         'Number charts, place value boards, counters', 3,
         'How do numbers help us make sense of the world around us?',
         'By end of lesson, the learner should be able to:\n(a) Read and write whole numbers up to millions.\n(b) Identify place value of digits in large numbers.\n(c) Apply knowledge of numbers to real-life situations.',
         '• Learner is guided to read and write large numbers.\n• Learner groups numbers using place value boards.\n• Learner discusses real-life contexts where large numbers are used.',
         'MTP Mathematics Grade 7 Learner\'s Book pp 1-20'),
        ('Integers',
         'Number line, integer cards, thermometer chart', 3,
         'How do negative numbers help us describe real-world situations?',
         'By end of lesson, the learner should be able to:\n(a) Define integers and represent them on a number line.\n(b) Add, subtract, multiply and divide integers.\n(c) Apply integers to real-life contexts (temperature, debt).',
         '• Learner uses number line to represent integers.\n• Learner performs operations on integers.\n• Learner applies integers to temperature and financial contexts.',
         'MTP Mathematics Grade 7 Learner\'s Book pp 21-40'),
        ('Fractions, Decimals and Percentages',
         'Fraction strips, decimal grids, percentage charts', 4,
         'How are fractions, decimals and percentages related?',
         'By end of lesson, the learner should be able to:\n(a) Convert between fractions, decimals and percentages.\n(b) Perform operations on fractions and decimals.\n(c) Apply percentage concepts to real-life problems.',
         '• Learner uses fraction strips to visualise fractions.\n• Learner converts between forms using decimal grids.\n• Real-life application: discounts, tax, interest.',
         'MTP Mathematics Grade 7 Learner\'s Book pp 41-65'),
    ], order=1)

    add_topic('math_junior', 'Algebra', [
        ('Algebraic Expressions',
         'Algebra tiles, charts', 3,
         'How can we use symbols to represent unknown quantities?',
         'By end of lesson, the learner should be able to:\n(a) Identify variables, constants and coefficients.\n(b) Simplify algebraic expressions by collecting like terms.\n(c) Expand and factorise simple expressions.',
         '• Learner uses algebra tiles to model expressions.\n• Learner simplifies expressions through guided practice.\n• Real-life situations modelled with algebraic expressions.',
         'MTP Mathematics Grade 8 Learner\'s Book pp 1-25'),
        ('Linear Equations',
         'Balance model, equation cards', 3,
         'How do we solve equations to find unknown values?',
         'By end of lesson, the learner should be able to:\n(a) Form and solve linear equations in one variable.\n(b) Form and solve simultaneous linear equations.\n(c) Apply linear equations to real-life word problems.',
         '• Learner uses balance model to solve equations.\n• Learner solves simultaneous equations by substitution and elimination.\n• Word problem solving in groups.',
         'MTP Mathematics Grade 8 Learner\'s Book pp 26-50'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # INTEGRATED SCIENCE — Junior (CBC)
    # ════════════════════════════════════════════════════════════
    add_topic('sci_junior', 'Scientific Investigation', [
        ('The Scientific Method',
         'Science laboratory, common objects for observation, worksheets', 2,
         'How do scientists investigate and solve problems?',
         'By end of lesson, the learner should be able to:\n(a) Describe the steps of the scientific method.\n(b) Formulate a hypothesis for a given problem.\n(c) Design a simple controlled experiment.',
         '• Learner is guided to identify a problem and ask questions.\n• Learner formulates hypotheses in groups.\n• Learner designs a simple experiment.',
         'MTP Integrated Science Grade 7 Learner\'s Book pp 1-18'),
        ('Safety in the Science Laboratory',
         'Laboratory safety posters, hazard symbols chart, first aid kit', 2,
         'Why is safety important when conducting science experiments?',
         'By end of lesson, the learner should be able to:\n(a) Identify safety rules in the science laboratory.\n(b) Recognise common hazard symbols.\n(c) Demonstrate correct handling of laboratory equipment.',
         '• Learner reads and discusses safety rules.\n• Learner identifies hazard symbols on chemical containers.\n• Role-play of safe laboratory practices.',
         'MTP Integrated Science Grade 7 Learner\'s Book pp 19-30'),
    ], order=1)

    add_topic('sci_junior', 'Matter and its Properties', [
        ('States of Matter',
         'Ice, water, kettle, syringes, balloons, graphs of heating curves', 3,
         'How does matter change from one state to another?',
         'By end of lesson, the learner should be able to:\n(a) Describe the three states of matter.\n(b) Explain changes of state using the particle model.\n(c) Relate changes of state to energy changes.',
         '• Learner observes melting of ice and evaporation of water.\n• Learner draws and interprets heating curves.\n• Discussion of everyday examples of state changes.',
         'MTP Integrated Science Grade 7 Learner\'s Book pp 35-55'),
        ('Mixtures and Separation Techniques',
         'Sand, salt, water, iron filings, magnet, filter paper, evaporating dish', 4,
         'How can we separate the components of a mixture?',
         'By end of lesson, the learner should be able to:\n(a) Distinguish between mixtures and pure substances.\n(b) Describe techniques for separating mixtures.\n(c) Select appropriate separation techniques for given mixtures.',
         '• Learner separates sand and iron filings using magnet.\n• Learner filters a soil-water mixture.\n• Learner evaporates salt solution to obtain salt.\n• Learner selects appropriate techniques for various mixtures.',
         'MTP Integrated Science Grade 7 Learner\'s Book pp 56-75'),
    ], order=2)

    add_topic('sci_junior', 'Living Things and Their Environment', [
        ('Classification of Living Things',
         'Charts of classification, specimens, hand lenses, reference books', 3,
         'Why do scientists classify living organisms?',
         'By end of lesson, the learner should be able to:\n(a) State the characteristics of living things.\n(b) Describe the classification system (Kingdom to Species).\n(c) Classify given organisms into major groups.',
         '• Learner observes specimens and identifies characteristics.\n• Learner uses dichotomous keys to classify organisms.\n• Learner researches local plants and animals.',
         'MTP Integrated Science Grade 8 Learner\'s Book pp 1-22'),
        ('Ecosystems and Food Chains',
         'Charts of ecosystems, food chain diagrams, local environment visit materials', 3,
         'How do organisms in an ecosystem depend on each other?',
         'By end of lesson, the learner should be able to:\n(a) Define an ecosystem and its components.\n(b) Construct and interpret food chains and food webs.\n(c) Explain the roles of producers, consumers and decomposers.',
         '• Learner constructs food chains from local organisms.\n• Learner builds a food web from food chains.\n• Discussion of effects of removing organisms from a food web.',
         'MTP Integrated Science Grade 8 Learner\'s Book pp 23-45'),
    ], order=3)

    # ════════════════════════════════════════════════════════════
    # SOCIAL STUDIES — Junior (CBC, Grade 9)
    # ════════════════════════════════════════════════════════════
    add_topic('social_junior', 'Citizenship and Social Responsibilities', [
        ('Rights and Responsibilities',
         'Kenya Constitution (extracts), charts of rights and responsibilities', 3,
         'What are the rights and responsibilities of citizens in Kenya?',
         'By end of lesson, the learner should be able to:\n(a) Define citizenship.\n(b) Identify rights and responsibilities of Kenyan citizens.\n(c) Apply citizenship values in their community.',
         '• Learner reads and discusses extracts from the Kenya Constitution.\n• Learner identifies examples of rights and responsibilities.\n• Learner role-plays citizenship scenarios.',
         'MTP Social Studies Grade 9 Learner\'s Book pp 1-20'),
        ('Governance and Democracy',
         'Charts of government structure, newspaper cuttings, Kenya Constitution', 3,
         'How is Kenya governed and how do citizens participate in governance?',
         'By end of lesson, the learner should be able to:\n(a) Describe the structure of Kenya\'s government.\n(b) Explain the principles of democracy.\n(c) Identify ways citizens participate in governance.',
         '• Learner studies charts of Kenya\'s government structure.\n• Discussion of elections and voting.\n• Learner identifies ways of civic participation.',
         'MTP Social Studies Grade 9 Learner\'s Book pp 21-40'),
    ], order=1)

    add_topic('social_junior', 'Economic Activities', [
        ('Agriculture in Kenya',
         'Maps of agricultural zones, photographs, charts of cash and food crops', 3,
         'How does agriculture contribute to Kenya\'s economy?',
         'By end of lesson, the learner should be able to:\n(a) Describe types of agriculture practised in Kenya.\n(b) Identify major cash and food crops.\n(c) Assess the contribution of agriculture to the Kenyan economy.',
         '• Learner studies maps of agricultural zones.\n• Discussion of factors affecting farming in Kenya.\n• Learner researches a cash crop of their choice.',
         'MTP Social Studies Grade 9 Learner\'s Book pp 45-70'),
        ('Industry and Trade',
         'Maps of industrial areas, photographs, charts of imports and exports', 3,
         'What role does industry and trade play in Kenya\'s development?',
         'By end of lesson, the learner should be able to:\n(a) Classify industries in Kenya.\n(b) Describe Kenya\'s major trade partners and commodities.\n(c) Explain the importance of the East African Community.',
         '• Learner maps industrial areas in Kenya.\n• Discussion of Kenya\'s main exports and imports.\n• Learner investigates benefits of EAC membership.',
         'MTP Social Studies Grade 9 Learner\'s Book pp 71-95'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # MATHEMATICS — Upper Primary (844)
    # ════════════════════════════════════════════════════════════
    add_topic('math_primary', 'Numbers', [
        ('Place Value',
         'Abacus, place value charts, number cards, counters', 3,
         'How do we understand and work with large numbers?',
         'By end of lesson learner should be able to:\n(a) Read and write numbers up to millions.\n(b) Identify the place value of each digit.\n(c) Round numbers to specified place values.',
         '• Teacher uses abacus to demonstrate place value.\n• Learners write numbers in expanded form.\n• Rounding exercises.',
         'Primary Mathematics KLB Std 5 pp 1-20'),
        ('Fractions',
         'Fraction charts, fraction strips, circular fraction models', 4,
         'How do fractions help us describe parts of a whole?',
         'By end of lesson learner should be able to:\n(a) Identify and compare fractions.\n(b) Add, subtract, multiply and divide fractions.\n(c) Apply fractions in real-life contexts.',
         '• Learners use fraction strips to compare fractions.\n• Teacher demonstrates operations on fractions.\n• Real-life word problems on fractions.',
         'Primary Mathematics KLB Std 5 pp 21-50'),
    ], order=1)

    add_topic('math_primary', 'Algebra', [
        ('Simple Equations',
         'Balance model, equation cards, counters', 3,
         'How can we use letters to represent unknown numbers?',
         'By end of lesson learner should be able to:\n(a) Form simple algebraic expressions.\n(b) Solve simple equations in one unknown.\n(c) Apply simple equations to word problems.',
         '• Teacher introduces idea of unknown using balance model.\n• Learners form and solve simple equations.\n• Word problem solving.',
         'Primary Mathematics KLB Std 7 pp 1-20'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # SCIENCE & TECHNOLOGY — Upper Primary (844)
    # ════════════════════════════════════════════════════════════
    add_topic('sci_primary', 'Living Things', [
        ('Plants and Their Parts',
         'Various plant specimens, hand lenses, charts of plant parts', 3,
         'How do the different parts of a plant help it to survive?',
         'By end of lesson learner should be able to:\n(a) Identify and name parts of a plant.\n(b) State the function of each part.\n(c) Appreciate the importance of plants to the environment.',
         '• Learners collect plant specimens and identify parts.\n• Teacher explains functions of plant parts.\n• Learners draw and label a plant.',
         'Primary Science KLB Std 4 pp 1-18'),
        ('Animals and Their Habitats',
         'Photographs of animals, habitat charts, reference books', 3,
         'Why do different animals live in different habitats?',
         'By end of lesson learner should be able to:\n(a) Define a habitat.\n(b) Identify animals and their natural habitats.\n(c) Explain how animals are adapted to their habitats.',
         '• Class discussion on various habitats.\n• Learners match animals to their habitats.\n• Research activity on animal adaptations.',
         'Primary Science KLB Std 4 pp 19-38'),
    ], order=1)

    add_topic('sci_primary', 'Matter', [
        ('States of Matter',
         'Ice, water, steam demonstration equipment, containers', 2,
         'How does matter change its form?',
         'By end of lesson learner should be able to:\n(a) Name the three states of matter.\n(b) Describe properties of solids, liquids and gases.\n(c) Give examples of changes of state in daily life.',
         '• Demonstration of melting ice and boiling water.\n• Learners classify objects as solid, liquid or gas.\n• Discussion of everyday changes of state.',
         'Primary Science KLB Std 5 pp 25-40'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # ENGLISH — Upper Primary (844)
    # ════════════════════════════════════════════════════════════
    add_topic('english_primary', 'Reading', [
        ('Reading Comprehension',
         'Set readers, newspapers, magazines, comprehension passages', 4,
         'How do we read for meaning and understanding?',
         'By end of lesson learner should be able to:\n(a) Read passages fluently and accurately.\n(b) Answer comprehension questions correctly.\n(c) Identify the main idea and supporting details.',
         '• Teacher reads passage aloud with learners.\n• Learners read silently and answer questions.\n• Discussion of vocabulary in context.',
         'KLB English Bk Std 5 pp 1-30'),
    ], order=1)

    add_topic('english_primary', 'Grammar', [
        ('Parts of Speech',
         'Grammar charts, sentence cards, textbooks', 3,
         'How do different words function in a sentence?',
         'By end of lesson learner should be able to:\n(a) Identify nouns, pronouns, verbs, adjectives and adverbs.\n(b) Use parts of speech correctly in sentences.\n(c) Edit sentences for grammatical correctness.',
         '• Teacher explains each part of speech with examples.\n• Learners identify parts of speech in passages.\n• Sentence construction exercise.',
         'KLB English Bk Std 6 pp 35-55'),
        ('Tenses',
         'Tense charts, verb cards, sentence strips', 3,
         'How do tenses help us communicate when events happen?',
         'By end of lesson learner should be able to:\n(a) Identify and use present, past and future tenses.\n(b) Convert sentences from one tense to another.\n(c) Write a paragraph using correct tenses.',
         '• Teacher introduces the concept of tense.\n• Learners convert sentences between tenses.\n• Writing exercise using correct tenses.',
         'KLB English Bk Std 6 pp 56-75'),
    ], order=2)

    # ════════════════════════════════════════════════════════════
    # SOCIAL STUDIES — Upper Primary (844)
    # ════════════════════════════════════════════════════════════
    add_topic('social_primary', 'Our Environment', [
        ('Natural Resources in Kenya',
         'Maps of Kenya showing resources, photographs, charts', 3,
         'What natural resources does Kenya have and how do we use them?',
         'By end of lesson learner should be able to:\n(a) Define natural resources.\n(b) Identify natural resources found in Kenya.\n(c) Explain the importance of conserving natural resources.',
         '• Teacher presents map of Kenya\'s natural resources.\n• Learners classify resources as renewable and non-renewable.\n• Discussion of conservation measures.',
         'Social Studies KLB Std 5 pp 1-25'),
    ], order=1)

    add_topic('social_primary', 'Kenya and East Africa', [
        ('Countries of East Africa',
         'Maps of East Africa, flags, atlas', 3,
         'Who are Kenya\'s neighbours and what do we share with them?',
         'By end of lesson learner should be able to:\n(a) Name the countries of East Africa.\n(b) Locate East African countries on a map.\n(c) State the importance of East African cooperation.',
         '• Learners label a blank map of East Africa.\n• Discussion of the East African Community.\n• Research on shared resources.',
         'Social Studies KLB Std 6 pp 30-55'),
    ], order=2)

    print("[SchemePro] Curriculum seed completed successfully.")
