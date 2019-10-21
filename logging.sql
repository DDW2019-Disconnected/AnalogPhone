create table if not exists dials (
 id INTEGER primary key,
 digit INTEGER,
 TimeDialed DATETIME DEFAULT CURRENT_TIMESTAMP
);

create table if not exists plays (
 id INTEGER primary key,
 digit INTEGER,
 TimeDialed DATETIME DEFAULT CURRENT_TIMESTAMP
);