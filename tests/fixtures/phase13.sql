-- SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
-- Synthetic Phase 13 audit/legacy/draft fixture, captured before conversion code removal.
BEGIN TRANSACTION;
CREATE TABLE basis_assignments (
    transition_id TEXT NOT NULL REFERENCES basis_transitions(id) ON DELETE CASCADE,
    workout_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    entry_id TEXT NOT NULL,
    before_basis TEXT NOT NULL CHECK(before_basis IN ('not_configured','total','per_side')),
    after_basis TEXT NOT NULL CHECK(after_basis IN ('total','per_side')),
    before_weight INTEGER CHECK(before_weight IS NULL OR before_weight>=0),
    after_weight INTEGER CHECK(after_weight IS NULL OR after_weight>=0),
    correction_id TEXT NOT NULL REFERENCES workout_corrections(id) ON DELETE CASCADE,
    PRIMARY KEY(transition_id,workout_id,entry_id),
    FOREIGN KEY(workout_id,person_id) REFERENCES workout_registry(id,person_id) ON DELETE CASCADE,
    CHECK((before_weight IS NULL)=(after_weight IS NULL)),
    CHECK(before_basis!=after_basis)
 ) STRICT;
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','d94425d07403443dbe6a71e460b5a77b','not_configured','total',400,400,'225a3d6cd89f471c80622f29b228b339');
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','bf19de9409ff48879b2a94b0fb1e53e5','not_configured','total',400,400,'078ccf8c337a4f04924e8d5dd5bb5500');
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','745c7b4431ce46ec85a0d3fd5ce7215a','not_configured','total',NULL,NULL,'4e8149c71e63447da4b55900277e250d');
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','7bc42c87198942eb9919b2732c2b51fd','not_configured','total',0,0,'e6792ea624884b42a00889135e66b7a7');
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','1791b55ef8174ede93bcc98eb74ce948','not_configured','total',500,500,'5737d4c9920f4f92abf4f9874fbd1a90');
INSERT INTO "basis_assignments" VALUES('45eaca6003704fb982258fd9a39aa60a','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','7ccbd86c0313433c8dc94af4e5bf518e','not_configured','total',500,500,'809b04466adf4fb382bf7b5dcaaaf38c');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','d94425d07403443dbe6a71e460b5a77b','total','per_side',400,200,'cfd5ced85ccc4a7ba02effad371cf39d');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','bf19de9409ff48879b2a94b0fb1e53e5','total','per_side',400,200,'13bb91b13f2c4894a76dfbbef57875fa');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','745c7b4431ce46ec85a0d3fd5ce7215a','total','per_side',NULL,NULL,'dd53009f8b254abdafdb2591e42f70e7');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','7bc42c87198942eb9919b2732c2b51fd','total','per_side',0,0,'84810c56c37a404081e0b4efa0b4e445');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','1791b55ef8174ede93bcc98eb74ce948','total','per_side',500,250,'6890406f975e4fa3be87a4ea3612b7de');
INSERT INTO "basis_assignments" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','7ccbd86c0313433c8dc94af4e5bf518e','total','per_side',500,250,'5438229f72544b3eb3f870b019a75fcd');
INSERT INTO "basis_assignments" VALUES('1c384692128949318273002a87200f9b','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e','a3c9237aed834ad6aad9f0f49a8bec6e','da2499523dee4b7c9321a2f08cf69618','not_configured','total',400,400,'21088e8cd4a546da9eef6283bf1c48f4');
INSERT INTO "basis_assignments" VALUES('aa6a12820ca44e72ba11bf3c13b13566','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e','a3c9237aed834ad6aad9f0f49a8bec6e','da2499523dee4b7c9321a2f08cf69618','total','per_side',400,200,'c752327220fa47a2a387a2370d5919a9');
CREATE TABLE basis_transitions (
    id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=32),
    person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
    exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK(revision>0),
    old_basis TEXT NOT NULL CHECK(old_basis IN ('not_configured','total','per_side')),
    new_basis TEXT NOT NULL CHECK(new_basis IN ('not_configured','total','per_side')),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
    effects_json TEXT NOT NULL,
    UNIQUE(person_id,exercise_id,revision),
    CHECK(old_basis='not_configured' OR new_basis!='not_configured')
 ) STRICT;
INSERT INTO "basis_transitions" VALUES('45eaca6003704fb982258fd9a39aa60a','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e',1,'not_configured','total','2026-11-11T16:38:34.439822+00:00','{"measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_basis":"total","weight_meaning":"old free text"}','192cfd5d591988fc94aec5beb8e6514e06eb4644110ed874b7c0172c992efc09','[{"after_basis":"total","after_weight":400,"before_basis":"not_configured","before_weight":400,"correction_id":"225a3d6cd89f471c80622f29b228b339","entry_id":"d94425d07403443dbe6a71e460b5a77b","workout_id":"4b5e4d4492254a3ca64dbc39f041858d"},{"after_basis":"total","after_weight":400,"before_basis":"not_configured","before_weight":400,"correction_id":"078ccf8c337a4f04924e8d5dd5bb5500","entry_id":"bf19de9409ff48879b2a94b0fb1e53e5","workout_id":"8b111d0638044b9fbd963468fe2a0ed4"},{"after_basis":"total","after_weight":null,"before_basis":"not_configured","before_weight":null,"correction_id":"4e8149c71e63447da4b55900277e250d","entry_id":"745c7b4431ce46ec85a0d3fd5ce7215a","workout_id":"6b6341474ea9499c8408c4142b8c2448"},{"after_basis":"total","after_weight":0,"before_basis":"not_configured","before_weight":0,"correction_id":"e6792ea624884b42a00889135e66b7a7","entry_id":"7bc42c87198942eb9919b2732c2b51fd","workout_id":"eb8998a9b0994fb697eefe4fc49baac1"},{"after_basis":"total","after_weight":500,"before_basis":"not_configured","before_weight":500,"correction_id":"5737d4c9920f4f92abf4f9874fbd1a90","entry_id":"1791b55ef8174ede93bcc98eb74ce948","workout_id":"7c372930d0604220a1bc4642ec182059"},{"after_basis":"total","after_weight":500,"before_basis":"not_configured","before_weight":500,"correction_id":"809b04466adf4fb382bf7b5dcaaaf38c","entry_id":"7ccbd86c0313433c8dc94af4e5bf518e","workout_id":"348462b9e6184389812002a63d73f7fa"}]');
INSERT INTO "basis_transitions" VALUES('8a3c6617140d4d2aa1da72a2d8df8601','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e',2,'total','per_side','2026-11-11T16:38:34.446159+00:00','{"measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_basis":"per_side","weight_meaning":"old free text"}','dd0884654a30d282e98a6d6afb5a59044b4d41ba48865abe74df3037b5d6c001','[{"after_basis":"per_side","after_weight":200,"before_basis":"total","before_weight":400,"correction_id":"cfd5ced85ccc4a7ba02effad371cf39d","entry_id":"d94425d07403443dbe6a71e460b5a77b","workout_id":"4b5e4d4492254a3ca64dbc39f041858d"},{"after_basis":"per_side","after_weight":200,"before_basis":"total","before_weight":400,"correction_id":"13bb91b13f2c4894a76dfbbef57875fa","entry_id":"bf19de9409ff48879b2a94b0fb1e53e5","workout_id":"8b111d0638044b9fbd963468fe2a0ed4"},{"after_basis":"per_side","after_weight":null,"before_basis":"total","before_weight":null,"correction_id":"dd53009f8b254abdafdb2591e42f70e7","entry_id":"745c7b4431ce46ec85a0d3fd5ce7215a","workout_id":"6b6341474ea9499c8408c4142b8c2448"},{"after_basis":"per_side","after_weight":0,"before_basis":"total","before_weight":0,"correction_id":"84810c56c37a404081e0b4efa0b4e445","entry_id":"7bc42c87198942eb9919b2732c2b51fd","workout_id":"eb8998a9b0994fb697eefe4fc49baac1"},{"after_basis":"per_side","after_weight":250,"before_basis":"total","before_weight":500,"correction_id":"6890406f975e4fa3be87a4ea3612b7de","entry_id":"1791b55ef8174ede93bcc98eb74ce948","workout_id":"7c372930d0604220a1bc4642ec182059"},{"after_basis":"per_side","after_weight":250,"before_basis":"total","before_weight":500,"correction_id":"5438229f72544b3eb3f870b019a75fcd","entry_id":"7ccbd86c0313433c8dc94af4e5bf518e","workout_id":"348462b9e6184389812002a63d73f7fa"}]');
INSERT INTO "basis_transitions" VALUES('1c384692128949318273002a87200f9b','2294fe0f56fb4b4e97dfcbf5d8a75a9e','a3c9237aed834ad6aad9f0f49a8bec6e',1,'not_configured','total','2026-11-11T16:38:34.450636+00:00','{"measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_basis":"total","weight_meaning":"old free text"}','192cfd5d591988fc94aec5beb8e6514e06eb4644110ed874b7c0172c992efc09','[{"after_basis":"total","after_weight":400,"before_basis":"not_configured","before_weight":400,"correction_id":"21088e8cd4a546da9eef6283bf1c48f4","entry_id":"da2499523dee4b7c9321a2f08cf69618","workout_id":"c95cba0105824c239b4a1d04fcc86681"}]');
INSERT INTO "basis_transitions" VALUES('aa6a12820ca44e72ba11bf3c13b13566','2294fe0f56fb4b4e97dfcbf5d8a75a9e','a3c9237aed834ad6aad9f0f49a8bec6e',2,'total','per_side','2026-11-11T16:38:34.455458+00:00','{"measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_basis":"per_side","weight_meaning":"old free text"}','dd0884654a30d282e98a6d6afb5a59044b4d41ba48865abe74df3037b5d6c001','[{"after_basis":"per_side","after_weight":200,"before_basis":"total","before_weight":400,"correction_id":"c752327220fa47a2a387a2370d5919a9","entry_id":"da2499523dee4b7c9321a2f08cf69618","workout_id":"c95cba0105824c239b4a1d04fcc86681"}]');
CREATE TABLE exercise_defaults (
    exercise_id TEXT PRIMARY KEY NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    weight_basis TEXT NOT NULL DEFAULT 'not_configured' CHECK(weight_basis IN ('not_configured','total','per_side')) CHECK(measurement_type!='time' OR weight_basis='not_configured'),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time','weight_duration')),
    target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
    target_reps INTEGER,
    target_duration_seconds INTEGER,
    unit TEXT,
    weight_meaning TEXT NOT NULL DEFAULT '' CHECK(length(weight_meaning)<=200),
    notes TEXT NOT NULL DEFAULT '' CHECK(length(notes)<=2000),
    CHECK((measurement_type='weight' AND target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000
           AND target_duration_seconds IS NULL AND unit IS NOT NULL AND unit='lb')
       OR (measurement_type='time' AND target_reps IS NULL AND target_duration_seconds IS NOT NULL
           AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL AND weight_meaning='') OR (measurement_type='weight_duration' AND target_reps IS NULL
        AND target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999
        AND unit IS NOT NULL AND unit='lb'))
) STRICT;
INSERT INTO "exercise_defaults" VALUES('a3c9237aed834ad6aad9f0f49a8bec6e','per_side','weight',3,12,NULL,'lb','old free text','Keep defaults');
INSERT INTO "exercise_defaults" VALUES('74c9aca8006740f49b10a3ab19525c56','not_configured','time',2,NULL,45,NULL,'','');
CREATE TABLE exercises (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
        UNIQUE(id, person_id)
    ) STRICT;
INSERT INTO "exercises" VALUES('a3c9237aed834ad6aad9f0f49a8bec6e','664bada8fb1e4d82b0198a02e2bf2b4b','Shared carry',0);
INSERT INTO "exercises" VALUES('74c9aca8006740f49b10a3ab19525c56','664bada8fb1e4d82b0198a02e2bf2b4b','Plank',0);
CREATE TABLE historical_entries (
        id TEXT PRIMARY KEY NOT NULL,
        session_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        name TEXT NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        weight_basis TEXT NOT NULL DEFAULT 'not_configured' CHECK(weight_basis IN ('not_configured','total','per_side')) CHECK(measurement_type!='time' OR weight_basis='not_configured'),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time','weight_duration')),
        target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
        target_reps INTEGER,
        target_duration_seconds INTEGER,
        unit TEXT,
        weight_meaning TEXT NOT NULL,
        notes TEXT NOT NULL,
        actual_weight_tenths_lb INTEGER CHECK(actual_weight_tenths_lb >= 0),
        actual_duration_seconds INTEGER CHECK(actual_duration_seconds >= 1),
        increase_next_time INTEGER CHECK(increase_next_time IN (0,1)),
        FOREIGN KEY(session_id,person_id) REFERENCES historical_workouts(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT,
        UNIQUE(session_id,position),
        CHECK((measurement_type='weight' AND target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000
                AND target_duration_seconds IS NULL AND unit IS NOT NULL AND unit='lb' AND actual_duration_seconds IS NULL)
           OR (measurement_type='time' AND target_reps IS NULL AND target_duration_seconds IS NOT NULL
                AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL AND weight_meaning=''
                AND actual_weight_tenths_lb IS NULL) OR (measurement_type='weight_duration' AND target_reps IS NULL
        AND target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999
        AND unit IS NOT NULL AND unit='lb' AND ((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL)
          OR (actual_weight_tenths_lb IS NOT NULL AND actual_duration_seconds IS NOT NULL)))),
        CHECK((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL AND increase_next_time IS NULL)
           OR ((actual_weight_tenths_lb IS NOT NULL OR actual_duration_seconds IS NOT NULL) AND increase_next_time IS NOT NULL))
    ) STRICT;
INSERT INTO "historical_entries" VALUES('7ccbd86c0313433c8dc94af4e5bf518e','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',250,NULL,1);
INSERT INTO "historical_entries" VALUES('d6e64cb3ce354f3d81cdbb04c441ff8d','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,45,0);
INSERT INTO "historical_entries" VALUES('1791b55ef8174ede93bcc98eb74ce948','7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight_duration',2,NULL,60,'lb','legacy hold','Historical prescription',500,90,0);
INSERT INTO "historical_entries" VALUES('7bc42c87198942eb9919b2732c2b51fd','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',0,NULL,0);
INSERT INTO "historical_entries" VALUES('3d75ff03922a41bd8ca9a25874d90417','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
INSERT INTO "historical_entries" VALUES('745c7b4431ce46ec85a0d3fd5ce7215a','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',NULL,NULL,NULL);
INSERT INTO "historical_entries" VALUES('ab5b924f891f406680bdbe28aaffdbf3','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
INSERT INTO "historical_entries" VALUES('da2499523dee4b7c9321a2f08cf69618','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',400,NULL,0);
INSERT INTO "historical_entries" VALUES('bd1bf8ecc071432bada5b160422a98e0','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
INSERT INTO "historical_entries" VALUES('bf19de9409ff48879b2a94b0fb1e53e5','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',400,NULL,0);
INSERT INTO "historical_entries" VALUES('41edf9f5901f456db2f09bd449819265','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
CREATE TABLE historical_forms (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        workout_time TEXT,
        occurred_at TEXT,
        prepared_at TEXT NOT NULL,
        snapshots_json TEXT NOT NULL,
        UNIQUE(id,person_id)
    ) STRICT;
INSERT INTO "historical_forms" VALUES('c0f03f7a856a4d67bea62fb417cecb97','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-01',NULL,NULL,'2026-11-11T16:38:34.403464+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"6da15dca63eb4c9cb249965c09e4543b","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_meaning":"old free text"},{"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"145754e1ba2d4e14b0b751df498e4c1c","measurement_type":"time","name":"Plank","notes":"","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":1,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_meaning":""}]');
INSERT INTO "historical_forms" VALUES('f7fc48871e1346b5a0280c9ba172ffa2','664bada8fb1e4d82b0198a02e2bf2b4b','410b3785a80042dc83a552865d21f5bd','Combined routine','UTC','2020-01-02',NULL,NULL,'2026-11-11T16:38:34.404957+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"40623c4a2b3348059e5ace53d91bfcb5","measurement_type":"weight_duration","name":"Shared carry","notes":"Historical prescription","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"410b3785a80042dc83a552865d21f5bd","target_duration_seconds":60,"target_reps":null,"target_sets":2,"unit":"lb","weight_meaning":"legacy hold"}]');
INSERT INTO "historical_forms" VALUES('938791fc005a488e90c28fd678e49be2','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-03',NULL,NULL,'2026-11-11T16:38:34.405086+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"6da15dca63eb4c9cb249965c09e4543b","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_meaning":"old free text"},{"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"145754e1ba2d4e14b0b751df498e4c1c","measurement_type":"time","name":"Plank","notes":"","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":1,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_meaning":""}]');
INSERT INTO "historical_forms" VALUES('fa0407953bd048239e829390a24c1b9c','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-04',NULL,NULL,'2026-11-11T16:38:34.405199+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"6da15dca63eb4c9cb249965c09e4543b","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_meaning":"old free text"},{"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"145754e1ba2d4e14b0b751df498e4c1c","measurement_type":"time","name":"Plank","notes":"","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":1,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_meaning":""}]');
INSERT INTO "historical_forms" VALUES('ad6d2110d4bf435fb8847e83c7364403','2294fe0f56fb4b4e97dfcbf5d8a75a9e','783821523dda401496b5ea8328c4f5e5','B copy','UTC','2020-01-01',NULL,NULL,'2026-11-11T16:38:34.405294+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"91b6fbaa10704893b7f38e22efbd8c52","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"2294fe0f56fb4b4e97dfcbf5d8a75a9e","position":0,"routine_id":"783821523dda401496b5ea8328c4f5e5","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_meaning":"old free text"},{"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"dcf7e7d050a44aa29153fd377789dbc3","measurement_type":"time","name":"Plank","notes":"","person_id":"2294fe0f56fb4b4e97dfcbf5d8a75a9e","position":1,"routine_id":"783821523dda401496b5ea8328c4f5e5","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_meaning":""}]');
INSERT INTO "historical_forms" VALUES('325a34817023403c928c3dbcbbc706e4','664bada8fb1e4d82b0198a02e2bf2b4b','954ad87e79f2415398fad410aaea2025','Removed routine','UTC','2020-01-05',NULL,NULL,'2026-11-11T16:38:34.406552+00:00','[{"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"0e1665f7ae724ae7af114bb6499cfb46","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"954ad87e79f2415398fad410aaea2025","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_meaning":"old free text"},{"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"2d40b11abc814702be04de0d5d4679d4","measurement_type":"time","name":"Plank","notes":"","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":1,"routine_id":"954ad87e79f2415398fad410aaea2025","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_meaning":""}]');
INSERT INTO "historical_forms" VALUES('220617e6d9b843df91c028e7cd8653d2','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-02-01',NULL,NULL,'2026-11-11T16:38:34.459630+00:00','[{"basis_epoch":2,"exercise_id":"a3c9237aed834ad6aad9f0f49a8bec6e","id":"6da15dca63eb4c9cb249965c09e4543b","measurement_type":"weight","name":"Shared carry","notes":"Keep defaults","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":0,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":null,"target_reps":12,"target_sets":3,"unit":"lb","weight_basis":"per_side","weight_meaning":"old free text"},{"basis_epoch":0,"exercise_id":"74c9aca8006740f49b10a3ab19525c56","id":"145754e1ba2d4e14b0b751df498e4c1c","measurement_type":"time","name":"Plank","notes":"","person_id":"664bada8fb1e4d82b0198a02e2bf2b4b","position":1,"routine_id":"ee7d5a479a4d4c4c99c5a137af9bcc15","target_duration_seconds":45,"target_reps":null,"target_sets":2,"unit":null,"weight_basis":"not_configured","weight_meaning":""}]');
CREATE TABLE historical_workouts (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        workout_time TEXT,
        occurred_at TEXT,
        entered_at TEXT NOT NULL,
        form_id TEXT NOT NULL UNIQUE,
        entry_count INTEGER NOT NULL CHECK(entry_count > 0),
        UNIQUE(id,person_id),
        FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE RESTRICT,
        FOREIGN KEY(form_id,person_id) REFERENCES historical_forms(id,person_id) ON DELETE RESTRICT,
        CHECK((workout_time IS NULL AND occurred_at IS NULL) OR (workout_time IS NOT NULL AND occurred_at IS NOT NULL))
    ) STRICT;
INSERT INTO "historical_workouts" VALUES('348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-01',NULL,NULL,'2026-11-11T16:38:34.403850+00:00','c0f03f7a856a4d67bea62fb417cecb97',2);
INSERT INTO "historical_workouts" VALUES('7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b','410b3785a80042dc83a552865d21f5bd','Combined routine','UTC','2020-01-02',NULL,NULL,'2026-11-11T16:38:34.405023+00:00','f7fc48871e1346b5a0280c9ba172ffa2',1);
INSERT INTO "historical_workouts" VALUES('eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-03',NULL,NULL,'2026-11-11T16:38:34.405138+00:00','938791fc005a488e90c28fd678e49be2',2);
INSERT INTO "historical_workouts" VALUES('6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2020-01-04',NULL,NULL,'2026-11-11T16:38:34.405241+00:00','fa0407953bd048239e829390a24c1b9c',2);
INSERT INTO "historical_workouts" VALUES('c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e','783821523dda401496b5ea8328c4f5e5','B copy','UTC','2020-01-01',NULL,NULL,'2026-11-11T16:38:34.405374+00:00','ad6d2110d4bf435fb8847e83c7364403',2);
INSERT INTO "historical_workouts" VALUES('8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b','954ad87e79f2415398fad410aaea2025','Removed routine','UTC','2020-01-05',NULL,NULL,'2026-11-11T16:38:34.406612+00:00','325a34817023403c928c3dbcbbc706e4',2);
CREATE TABLE people (
        id TEXT PRIMARY KEY NOT NULL,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1))
    ) STRICT;
INSERT INTO "people" VALUES('664bada8fb1e4d82b0198a02e2bf2b4b','A',0);
INSERT INTO "people" VALUES('2294fe0f56fb4b4e97dfcbf5d8a75a9e','B',0);
CREATE TABLE routine_exercises (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        weight_basis TEXT NOT NULL DEFAULT 'not_configured' CHECK(weight_basis IN ('not_configured','total','per_side')) CHECK(measurement_type!='time' OR weight_basis='not_configured'),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time','weight_duration')),
        target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
        target_reps INTEGER,
        target_duration_seconds INTEGER,
        unit TEXT,
        weight_meaning TEXT NOT NULL DEFAULT '' CHECK(length(weight_meaning) <= 200),
        notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 2000),
        FOREIGN KEY(routine_id, person_id) REFERENCES routines(id, person_id) ON DELETE RESTRICT,
        FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT,
        UNIQUE(routine_id, position),
        CHECK((measurement_type = 'weight' AND target_reps IS NOT NULL
               AND target_reps BETWEEN 1 AND 10000 AND target_duration_seconds IS NULL
               AND unit IS NOT NULL AND unit = 'lb')
           OR (measurement_type = 'time' AND target_reps IS NULL
               AND target_duration_seconds IS NOT NULL
               AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL
               AND weight_meaning = '') OR (measurement_type='weight_duration' AND target_reps IS NULL
        AND target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999
        AND unit IS NOT NULL AND unit='lb'))
    ) STRICT;
INSERT INTO "routine_exercises" VALUES('6da15dca63eb4c9cb249965c09e4543b','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','a3c9237aed834ad6aad9f0f49a8bec6e',0,'per_side','weight',3,12,NULL,'lb','old free text','Keep defaults');
INSERT INTO "routine_exercises" VALUES('145754e1ba2d4e14b0b751df498e4c1c','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','74c9aca8006740f49b10a3ab19525c56',1,'not_configured','time',2,NULL,45,NULL,'','');
INSERT INTO "routine_exercises" VALUES('91b6fbaa10704893b7f38e22efbd8c52','2294fe0f56fb4b4e97dfcbf5d8a75a9e','783821523dda401496b5ea8328c4f5e5','a3c9237aed834ad6aad9f0f49a8bec6e',0,'per_side','weight',3,12,NULL,'lb','old free text','Keep defaults');
INSERT INTO "routine_exercises" VALUES('dcf7e7d050a44aa29153fd377789dbc3','2294fe0f56fb4b4e97dfcbf5d8a75a9e','783821523dda401496b5ea8328c4f5e5','74c9aca8006740f49b10a3ab19525c56',1,'not_configured','time',2,NULL,45,NULL,'','');
INSERT INTO "routine_exercises" VALUES('40623c4a2b3348059e5ace53d91bfcb5','664bada8fb1e4d82b0198a02e2bf2b4b','410b3785a80042dc83a552865d21f5bd','a3c9237aed834ad6aad9f0f49a8bec6e',0,'per_side','weight',3,12,NULL,'lb','old free text','Keep defaults');
CREATE TABLE routines (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
        position INTEGER NOT NULL CHECK(position >= 0),
        archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0, 1)),
        UNIQUE(id, person_id),
        UNIQUE(person_id, position)
    ) STRICT;
INSERT INTO "routines" VALUES('ee7d5a479a4d4c4c99c5a137af9bcc15','664bada8fb1e4d82b0198a02e2bf2b4b','Weight routine',0,0);
INSERT INTO "routines" VALUES('783821523dda401496b5ea8328c4f5e5','2294fe0f56fb4b4e97dfcbf5d8a75a9e','B copy',0,0);
INSERT INTO "routines" VALUES('410b3785a80042dc83a552865d21f5bd','664bada8fb1e4d82b0198a02e2bf2b4b','Combined routine',1,0);
CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    ) STRICT;
INSERT INTO "schema_migrations" VALUES(1,'foundation');
INSERT INTO "schema_migrations" VALUES(2,'people_and_routines');
INSERT INTO "schema_migrations" VALUES(3,'workout_tracking');
INSERT INTO "schema_migrations" VALUES(4,'history_and_corrections');
INSERT INTO "schema_migrations" VALUES(5,'shared_exercise_library');
INSERT INTO "schema_migrations" VALUES(6,'permanent_deletion');
INSERT INTO "schema_migrations" VALUES(7,'exercise_defaults');
INSERT INTO "schema_migrations" VALUES(8,'combined_weight_duration');
INSERT INTO "schema_migrations" VALUES(9,'weight_basis_transition');
CREATE TABLE storage_metadata (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        storage_id TEXT NOT NULL UNIQUE
    ) STRICT;
INSERT INTO "storage_metadata" VALUES(1,'53b6e342411842f99d44c683802e3ffd');
CREATE TABLE workout_corrections (
        id TEXT PRIMARY KEY NOT NULL,
        workout_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision >= 1),
        corrected_at TEXT NOT NULL,
        before_json TEXT NOT NULL,
        after_json TEXT NOT NULL,
        UNIQUE(workout_id,revision),
        FOREIGN KEY(workout_id,person_id) REFERENCES workout_registry(id,person_id) ON DELETE RESTRICT
    ) STRICT;
INSERT INTO "workout_corrections" VALUES('884a30ff0eb2424086fc17e21e4b2ffe','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.404710+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":250,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":500,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('225a3d6cd89f471c80622f29b228b339','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"d94425d07403443dbe6a71e460b5a77b","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"2d4d36c29e2a45679d937ba4157dccc9","increase_next_time":null}],"occurred_at":"2026-11-11T16:38:34.405460+00:00","workout_date":"2026-11-11","workout_time":"16:38:34"}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"d94425d07403443dbe6a71e460b5a77b","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"2d4d36c29e2a45679d937ba4157dccc9","increase_next_time":null}],"occurred_at":"2026-11-11T16:38:34.405460+00:00","workout_date":"2026-11-11","workout_time":"16:38:34"}');
INSERT INTO "workout_corrections" VALUES('078ccf8c337a4f04924e8d5dd5bb5500','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"bf19de9409ff48879b2a94b0fb1e53e5","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"41edf9f5901f456db2f09bd449819265","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-05","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"bf19de9409ff48879b2a94b0fb1e53e5","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"41edf9f5901f456db2f09bd449819265","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-05","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('4e8149c71e63447da4b55900277e250d','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"745c7b4431ce46ec85a0d3fd5ce7215a","increase_next_time":null},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"ab5b924f891f406680bdbe28aaffdbf3","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-04","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"745c7b4431ce46ec85a0d3fd5ce7215a","increase_next_time":null},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"ab5b924f891f406680bdbe28aaffdbf3","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-04","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('e6792ea624884b42a00889135e66b7a7','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":0,"id":"7bc42c87198942eb9919b2732c2b51fd","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"3d75ff03922a41bd8ca9a25874d90417","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-03","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":0,"id":"7bc42c87198942eb9919b2732c2b51fd","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"3d75ff03922a41bd8ca9a25874d90417","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-03","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('5737d4c9920f4f92abf4f9874fbd1a90','7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b',1,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":90,"actual_weight_tenths_lb":500,"id":"1791b55ef8174ede93bcc98eb74ce948","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-02","workout_time":null}','{"entries":[{"actual_duration_seconds":90,"actual_weight_tenths_lb":500,"id":"1791b55ef8174ede93bcc98eb74ce948","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-02","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('809b04466adf4fb382bf7b5dcaaaf38c','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.439822+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":500,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":500,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('cfd5ced85ccc4a7ba02effad371cf39d','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"d94425d07403443dbe6a71e460b5a77b","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"2d4d36c29e2a45679d937ba4157dccc9","increase_next_time":null}],"occurred_at":"2026-11-11T16:38:34.405460+00:00","workout_date":"2026-11-11","workout_time":"16:38:34"}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":200,"id":"d94425d07403443dbe6a71e460b5a77b","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"2d4d36c29e2a45679d937ba4157dccc9","increase_next_time":null}],"occurred_at":"2026-11-11T16:38:34.405460+00:00","workout_date":"2026-11-11","workout_time":"16:38:34"}');
INSERT INTO "workout_corrections" VALUES('13bb91b13f2c4894a76dfbbef57875fa','8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"bf19de9409ff48879b2a94b0fb1e53e5","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"41edf9f5901f456db2f09bd449819265","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-05","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":200,"id":"bf19de9409ff48879b2a94b0fb1e53e5","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"41edf9f5901f456db2f09bd449819265","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-05","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('dd53009f8b254abdafdb2591e42f70e7','6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"745c7b4431ce46ec85a0d3fd5ce7215a","increase_next_time":null},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"ab5b924f891f406680bdbe28aaffdbf3","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-04","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"745c7b4431ce46ec85a0d3fd5ce7215a","increase_next_time":null},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"ab5b924f891f406680bdbe28aaffdbf3","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-04","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('84810c56c37a404081e0b4efa0b4e445','eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":0,"id":"7bc42c87198942eb9919b2732c2b51fd","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"3d75ff03922a41bd8ca9a25874d90417","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-03","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":0,"id":"7bc42c87198942eb9919b2732c2b51fd","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"3d75ff03922a41bd8ca9a25874d90417","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-03","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('6890406f975e4fa3be87a4ea3612b7de','7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b',2,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":90,"actual_weight_tenths_lb":500,"id":"1791b55ef8174ede93bcc98eb74ce948","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-02","workout_time":null}','{"entries":[{"actual_duration_seconds":90,"actual_weight_tenths_lb":250,"id":"1791b55ef8174ede93bcc98eb74ce948","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-02","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('5438229f72544b3eb3f870b019a75fcd','348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b',3,'2026-11-11T16:38:34.446159+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":500,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":250,"id":"7ccbd86c0313433c8dc94af4e5bf518e","increase_next_time":1},{"actual_duration_seconds":45,"actual_weight_tenths_lb":null,"id":"d6e64cb3ce354f3d81cdbb04c441ff8d","increase_next_time":0}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('21088e8cd4a546da9eef6283bf1c48f4','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e',1,'2026-11-11T16:38:34.450636+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"da2499523dee4b7c9321a2f08cf69618","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"bd1bf8ecc071432bada5b160422a98e0","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"da2499523dee4b7c9321a2f08cf69618","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"bd1bf8ecc071432bada5b160422a98e0","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}');
INSERT INTO "workout_corrections" VALUES('c752327220fa47a2a387a2370d5919a9','c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e',2,'2026-11-11T16:38:34.455458+00:00','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":400,"id":"da2499523dee4b7c9321a2f08cf69618","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"bd1bf8ecc071432bada5b160422a98e0","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}','{"entries":[{"actual_duration_seconds":null,"actual_weight_tenths_lb":200,"id":"da2499523dee4b7c9321a2f08cf69618","increase_next_time":0},{"actual_duration_seconds":null,"actual_weight_tenths_lb":null,"id":"bd1bf8ecc071432bada5b160422a98e0","increase_next_time":null}],"occurred_at":null,"workout_date":"2020-01-01","workout_time":null}');
CREATE TABLE workout_entries (
        id TEXT PRIMARY KEY NOT NULL,
        session_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        name TEXT NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        weight_basis TEXT NOT NULL DEFAULT 'not_configured' CHECK(weight_basis IN ('not_configured','total','per_side')) CHECK(measurement_type!='time' OR weight_basis='not_configured'),
        measurement_type TEXT NOT NULL CHECK(measurement_type IN ('weight','time','weight_duration')),
        target_sets INTEGER NOT NULL CHECK(target_sets BETWEEN 1 AND 1000),
        target_reps INTEGER,
        target_duration_seconds INTEGER,
        unit TEXT,
        weight_meaning TEXT NOT NULL,
        notes TEXT NOT NULL,
        actual_weight_tenths_lb INTEGER CHECK(actual_weight_tenths_lb >= 0),
        actual_duration_seconds INTEGER CHECK(actual_duration_seconds >= 1),
        increase_next_time INTEGER CHECK(increase_next_time IN (0,1)),
        FOREIGN KEY(session_id,person_id) REFERENCES workout_sessions(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT,
        UNIQUE(session_id,position),
        CHECK((measurement_type='weight' AND target_reps IS NOT NULL AND target_reps BETWEEN 1 AND 10000
                AND target_duration_seconds IS NULL AND unit IS NOT NULL AND unit='lb' AND actual_duration_seconds IS NULL)
           OR (measurement_type='time' AND target_reps IS NULL AND target_duration_seconds IS NOT NULL
                AND target_duration_seconds BETWEEN 1 AND 359999 AND unit IS NULL AND weight_meaning=''
                AND actual_weight_tenths_lb IS NULL) OR (measurement_type='weight_duration' AND target_reps IS NULL
        AND target_duration_seconds IS NOT NULL AND target_duration_seconds BETWEEN 1 AND 359999
        AND unit IS NOT NULL AND unit='lb' AND ((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL)
          OR (actual_weight_tenths_lb IS NOT NULL AND actual_duration_seconds IS NOT NULL)))),
        CHECK((actual_weight_tenths_lb IS NULL AND actual_duration_seconds IS NULL AND increase_next_time IS NULL)
           OR ((actual_weight_tenths_lb IS NOT NULL OR actual_duration_seconds IS NOT NULL) AND increase_next_time IS NOT NULL))
    ) STRICT;
INSERT INTO "workout_entries" VALUES('d94425d07403443dbe6a71e460b5a77b','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'not_configured','weight',3,12,NULL,'lb','old free text','Keep defaults',400,NULL,0);
INSERT INTO "workout_entries" VALUES('2d4d36c29e2a45679d937ba4157dccc9','4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
INSERT INTO "workout_entries" VALUES('04cbaabbfbec49da9edb389939147d34','1818085744a44eafae76336d60b21381','664bada8fb1e4d82b0198a02e2bf2b4b','a3c9237aed834ad6aad9f0f49a8bec6e','Shared carry',0,'per_side','weight',3,12,NULL,'lb','old free text','Keep defaults',410,NULL,0);
INSERT INTO "workout_entries" VALUES('7a33cb67a8b3494fb3bee5a0c7edf6b5','1818085744a44eafae76336d60b21381','664bada8fb1e4d82b0198a02e2bf2b4b','74c9aca8006740f49b10a3ab19525c56','Plank',1,'not_configured','time',2,NULL,45,NULL,'','',NULL,NULL,NULL);
CREATE TABLE workout_registry (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL,
        live_session_id TEXT,
        historical_session_id TEXT,
        UNIQUE(id,person_id),
        FOREIGN KEY(live_session_id,person_id) REFERENCES workout_sessions(id,person_id) ON DELETE RESTRICT,
        FOREIGN KEY(historical_session_id,person_id) REFERENCES historical_workouts(id,person_id) ON DELETE RESTRICT,
        CHECK((live_session_id IS NOT NULL AND historical_session_id IS NULL AND id=live_session_id)
           OR (historical_session_id IS NOT NULL AND live_session_id IS NULL AND id=historical_session_id))
    ) STRICT;
INSERT INTO "workout_registry" VALUES('348462b9e6184389812002a63d73f7fa','664bada8fb1e4d82b0198a02e2bf2b4b',NULL,'348462b9e6184389812002a63d73f7fa');
INSERT INTO "workout_registry" VALUES('7c372930d0604220a1bc4642ec182059','664bada8fb1e4d82b0198a02e2bf2b4b',NULL,'7c372930d0604220a1bc4642ec182059');
INSERT INTO "workout_registry" VALUES('eb8998a9b0994fb697eefe4fc49baac1','664bada8fb1e4d82b0198a02e2bf2b4b',NULL,'eb8998a9b0994fb697eefe4fc49baac1');
INSERT INTO "workout_registry" VALUES('6b6341474ea9499c8408c4142b8c2448','664bada8fb1e4d82b0198a02e2bf2b4b',NULL,'6b6341474ea9499c8408c4142b8c2448');
INSERT INTO "workout_registry" VALUES('c95cba0105824c239b4a1d04fcc86681','2294fe0f56fb4b4e97dfcbf5d8a75a9e',NULL,'c95cba0105824c239b4a1d04fcc86681');
INSERT INTO "workout_registry" VALUES('4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','4b5e4d4492254a3ca64dbc39f041858d',NULL);
INSERT INTO "workout_registry" VALUES('8b111d0638044b9fbd963468fe2a0ed4','664bada8fb1e4d82b0198a02e2bf2b4b',NULL,'8b111d0638044b9fbd963468fe2a0ed4');
CREATE TABLE workout_sessions (
        id TEXT PRIMARY KEY NOT NULL,
        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        timezone TEXT NOT NULL,
        workout_date TEXT NOT NULL,
        started_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        finished_at TEXT,
        discarded_at TEXT,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','completed','discarded')),
        revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
        entry_count INTEGER NOT NULL CHECK(entry_count > 0),
        current_position INTEGER NOT NULL DEFAULT 0 CHECK(current_position >= 0 AND current_position < entry_count),
        UNIQUE(id,person_id),
        CHECK((status='draft' AND finished_at IS NULL AND discarded_at IS NULL)
           OR (status='completed' AND finished_at IS NOT NULL AND discarded_at IS NULL)
           OR (status='discarded' AND finished_at IS NULL AND discarded_at IS NOT NULL))
    ) STRICT;
INSERT INTO "workout_sessions" VALUES('4b5e4d4492254a3ca64dbc39f041858d','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2026-11-11','2026-11-11T16:38:34.405460+00:00','2026-11-11T16:38:34.406289+00:00','2026-11-11T16:38:34.406289+00:00',NULL,'completed',1,2,0);
INSERT INTO "workout_sessions" VALUES('1818085744a44eafae76336d60b21381','664bada8fb1e4d82b0198a02e2bf2b4b','ee7d5a479a4d4c4c99c5a137af9bcc15','Weight routine','UTC','2026-11-11','2026-11-11T16:38:34.458849+00:00','2026-11-11T16:38:34.459286+00:00',NULL,NULL,'draft',1,2,0);
CREATE UNIQUE INDEX one_active_workout ON workout_sessions(person_id) WHERE status='draft';
CREATE TRIGGER finished_session_immutable BEFORE UPDATE ON workout_sessions WHEN deletion_in_progress()=0 AND (OLD.status != 'draft') BEGIN SELECT RAISE(ABORT,'Finished session is immutable'); END;
CREATE TRIGGER session_delete_protected BEFORE DELETE ON workout_sessions WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Sessions must be retained'); END;
CREATE TRIGGER entry_snapshot_immutable BEFORE UPDATE ON workout_entries WHEN deletion_in_progress()=0 AND (OLD.id IS NOT NEW.id OR OLD.session_id IS NOT NEW.session_id OR OLD.person_id IS NOT NEW.person_id
          OR OLD.exercise_id IS NOT NEW.exercise_id OR OLD.name IS NOT NEW.name OR OLD.position IS NOT NEW.position
          OR OLD.measurement_type IS NOT NEW.measurement_type OR OLD.target_sets IS NOT NEW.target_sets
          OR OLD.target_reps IS NOT NEW.target_reps OR OLD.target_duration_seconds IS NOT NEW.target_duration_seconds
          OR OLD.unit IS NOT NEW.unit OR OLD.weight_meaning IS NOT NEW.weight_meaning OR OLD.notes IS NOT NEW.notes
          OR (SELECT status FROM workout_sessions WHERE id=OLD.session_id) != 'draft') BEGIN SELECT RAISE(ABORT,'Workout snapshot is immutable'); END;
CREATE TRIGGER entry_delete_protected BEFORE DELETE ON workout_entries WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Snapshot entries must be retained'); END;
CREATE TRIGGER entry_insert_protected BEFORE INSERT ON workout_entries WHEN deletion_in_progress()=0 AND ((SELECT status FROM workout_sessions WHERE id=NEW.session_id) != 'draft'
          OR NEW.position >= (SELECT entry_count FROM workout_sessions WHERE id=NEW.session_id)) BEGIN SELECT RAISE(ABORT,'Invalid snapshot insertion'); END;
CREATE TRIGGER session_completion_validated BEFORE UPDATE OF status ON workout_sessions WHEN deletion_in_progress()=0 AND (NEW.status='completed' AND (SELECT count(*) FROM workout_entries WHERE session_id=OLD.id) != OLD.entry_count) BEGIN SELECT RAISE(ABORT,'Incomplete workout snapshot'); END;
CREATE TRIGGER register_completed_workout AFTER UPDATE OF status ON workout_sessions
        WHEN NEW.status='completed' BEGIN
        INSERT INTO workout_registry(id,person_id,live_session_id) VALUES (NEW.id,NEW.person_id,NEW.id); END;
CREATE TRIGGER register_historical_workout AFTER INSERT ON historical_workouts BEGIN
        INSERT INTO workout_registry(id,person_id,historical_session_id) VALUES (NEW.id,NEW.person_id,NEW.id); END;
CREATE TRIGGER correction_revision_guard BEFORE INSERT ON workout_corrections WHEN deletion_in_progress()=0 AND (NEW.revision != (SELECT coalesce(max(revision),0)+1 FROM workout_corrections WHERE workout_id=NEW.workout_id)) BEGIN SELECT RAISE(ABORT,'Correction revision must append the next version'); END;
CREATE TRIGGER registry_completed_guard BEFORE INSERT ON workout_registry WHEN deletion_in_progress()=0 AND (NEW.live_session_id IS NOT NULL AND (SELECT status FROM workout_sessions WHERE id=NEW.live_session_id) != 'completed') BEGIN SELECT RAISE(ABORT,'Only completed workouts may have corrections'); END;
CREATE TRIGGER historical_entry_insert_guard BEFORE INSERT ON historical_entries WHEN deletion_in_progress()=0 AND (NEW.position >= (SELECT entry_count FROM historical_workouts WHERE id=NEW.session_id)
          OR EXISTS(SELECT 1 FROM workout_corrections WHERE workout_id=NEW.session_id)) BEGIN SELECT RAISE(ABORT,'Historical snapshot is finalized'); END;
CREATE TRIGGER historical_forms_update_protected BEFORE UPDATE ON historical_forms WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER historical_forms_delete_protected BEFORE DELETE ON historical_forms WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER historical_workouts_update_protected BEFORE UPDATE ON historical_workouts WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER historical_workouts_delete_protected BEFORE DELETE ON historical_workouts WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER historical_entries_update_protected BEFORE UPDATE ON historical_entries WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER historical_entries_delete_protected BEFORE DELETE ON historical_entries WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER workout_registry_update_protected BEFORE UPDATE ON workout_registry WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER workout_registry_delete_protected BEFORE DELETE ON workout_registry WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER workout_corrections_update_protected BEFORE UPDATE ON workout_corrections WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER workout_corrections_delete_protected BEFORE DELETE ON workout_corrections WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only history record'); END;
CREATE TRIGGER live_routine_owner_guard BEFORE INSERT ON workout_sessions
        WHEN NOT EXISTS(SELECT 1 FROM routines WHERE id=NEW.routine_id AND person_id=NEW.person_id)
        BEGIN SELECT RAISE(ABORT,'Routine ownership mismatch'); END;
CREATE TRIGGER prepared_routine_owner_guard BEFORE INSERT ON historical_forms
        WHEN NOT EXISTS(SELECT 1 FROM routines WHERE id=NEW.routine_id AND person_id=NEW.person_id)
        BEGIN SELECT RAISE(ABORT,'Routine ownership mismatch'); END;
CREATE TRIGGER historical_preparation_owner_guard BEFORE INSERT ON historical_workouts
        WHEN NOT EXISTS(SELECT 1 FROM historical_forms WHERE id=NEW.form_id AND person_id=NEW.person_id AND routine_id=NEW.routine_id)
        BEGIN SELECT RAISE(ABORT,'Historical preparation ownership mismatch'); END;
CREATE TRIGGER historical_basis_immutable BEFORE UPDATE OF weight_basis ON historical_entries BEGIN SELECT RAISE(ABORT,'Immutable original basis'); END;
CREATE TRIGGER workout_basis_immutable BEFORE UPDATE OF weight_basis ON workout_entries BEGIN SELECT RAISE(ABORT,'Immutable original basis'); END;
CREATE INDEX basis_entry_lookup ON basis_assignments(person_id,workout_id,entry_id);
CREATE TRIGGER basis_transition_order BEFORE INSERT ON basis_transitions
    WHEN NEW.revision!=(SELECT coalesce(max(revision),0)+1 FROM basis_transitions WHERE person_id=NEW.person_id AND exercise_id=NEW.exercise_id)
    OR NEW.old_basis!=coalesce((SELECT new_basis FROM basis_transitions WHERE person_id=NEW.person_id AND exercise_id=NEW.exercise_id ORDER BY revision DESC LIMIT 1),'not_configured')
    BEGIN SELECT RAISE(ABORT,'Basis revisions must append from the actual baseline'); END;
CREATE TRIGGER basis_assignment_identity BEFORE INSERT ON basis_assignments
    WHEN NOT EXISTS(SELECT 1 FROM basis_transitions WHERE id=NEW.transition_id AND person_id=NEW.person_id AND exercise_id=NEW.exercise_id)
      OR NOT EXISTS(SELECT 1 FROM workout_corrections WHERE id=NEW.correction_id AND workout_id=NEW.workout_id AND person_id=NEW.person_id)
      OR (NOT EXISTS(SELECT 1 FROM workout_entries e JOIN workout_sessions s ON s.id=e.session_id WHERE e.id=NEW.entry_id AND e.session_id=NEW.workout_id AND e.person_id=NEW.person_id AND e.exercise_id=NEW.exercise_id AND e.measurement_type IN ('weight','weight_duration') AND s.status='completed')
          AND NOT EXISTS(SELECT 1 FROM historical_entries WHERE id=NEW.entry_id AND session_id=NEW.workout_id AND person_id=NEW.person_id AND exercise_id=NEW.exercise_id AND measurement_type IN ('weight','weight_duration')))
    BEGIN SELECT RAISE(ABORT,'Basis assignment ownership or completed identity mismatch'); END;
CREATE TRIGGER basis_transitions_update_protected BEFORE UPDATE ON basis_transitions BEGIN SELECT RAISE(ABORT,'Append-only basis audit'); END;
CREATE TRIGGER basis_transitions_delete_protected BEFORE DELETE ON basis_transitions WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only basis audit'); END;
CREATE TRIGGER basis_assignments_update_protected BEFORE UPDATE ON basis_assignments BEGIN SELECT RAISE(ABORT,'Append-only basis audit'); END;
CREATE TRIGGER basis_assignments_delete_protected BEFORE DELETE ON basis_assignments WHEN deletion_in_progress()=0 BEGIN SELECT RAISE(ABORT,'Append-only basis audit'); END;
COMMIT;
PRAGMA user_version=9;
PRAGMA application_id=1465143883;
