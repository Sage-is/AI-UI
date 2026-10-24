-- The schema peewee built on a fresh database, frozen when peewee left (3.2.1).
--
-- Captured 2026-10-15 from the last build with peewee: the 19 migrations, alone
-- on an empty SQLite file, dumped from sqlite_master in creation order. Do not
-- edit. Schema changes go in alembic (sage_is_ai/migrations/versions/).
-- internal/legacy_db.py replays this on a fresh database, then alembic runs as
-- it always did, so a new install gets the same schema as every existing one.
-- Alembic alone builds a different shape (152 differing lines of .schema).
CREATE TABLE "migratehistory" ("id" INTEGER NOT NULL PRIMARY KEY, "name" VARCHAR(255) NOT NULL, "migrated_at" DATETIME NOT NULL);
CREATE TABLE "tag" ("id" VARCHAR(255) NOT NULL, "name" VARCHAR(255) NOT NULL, "user_id" VARCHAR(255) NOT NULL, "data" TEXT);
CREATE UNIQUE INDEX "tag_id" ON "tag" ("id");
CREATE TABLE "chatidtag" ("id" VARCHAR(255) NOT NULL, "tag_name" VARCHAR(255) NOT NULL, "chat_id" VARCHAR(255) NOT NULL, "user_id" VARCHAR(255) NOT NULL, "timestamp" INTEGER NOT NULL NOT NULL);
CREATE UNIQUE INDEX "chatidtag_id" ON "chatidtag" ("id");
CREATE TABLE "auth" ("id" VARCHAR(255) NOT NULL, "email" VARCHAR(255) NOT NULL, "password" TEXT NOT NULL NOT NULL, "active" INTEGER NOT NULL);
CREATE UNIQUE INDEX "auth_id" ON "auth" ("id");
CREATE TABLE "chat" ("id" VARCHAR(255) NOT NULL, "user_id" VARCHAR(255) NOT NULL, "title" TEXT NOT NULL NOT NULL, "chat" TEXT NOT NULL, "share_id" VARCHAR(255), "archived" INTEGER NOT NULL, "created_at" DATETIME NOT NULL NOT NULL, "updated_at" DATETIME NOT NULL NOT NULL);
CREATE UNIQUE INDEX "chat_id" ON "chat" ("id");
CREATE UNIQUE INDEX "chat_share_id" ON "chat" ("share_id");
CREATE TABLE "document" ("id" INTEGER NOT NULL PRIMARY KEY, "collection_name" VARCHAR(255) NOT NULL, "name" VARCHAR(255) NOT NULL, "title" TEXT NOT NULL NOT NULL, "filename" TEXT NOT NULL NOT NULL, "content" TEXT, "user_id" VARCHAR(255) NOT NULL, "timestamp" INTEGER NOT NULL NOT NULL);
CREATE UNIQUE INDEX "document_collection_name" ON "document" ("collection_name");
CREATE UNIQUE INDEX "document_name" ON "document" ("name");
CREATE TABLE "prompt" ("id" INTEGER NOT NULL PRIMARY KEY, "command" VARCHAR(255) NOT NULL, "user_id" VARCHAR(255) NOT NULL, "title" TEXT NOT NULL NOT NULL, "content" TEXT NOT NULL, "timestamp" INTEGER NOT NULL NOT NULL);
CREATE UNIQUE INDEX "prompt_command" ON "prompt" ("command");
CREATE TABLE "user" ("id" VARCHAR(255) NOT NULL, "name" VARCHAR(255) NOT NULL, "email" VARCHAR(255) NOT NULL, "role" VARCHAR(255) NOT NULL, "profile_image_url" TEXT NOT NULL NOT NULL, "api_key" VARCHAR(255), "created_at" INTEGER NOT NULL NOT NULL, "updated_at" INTEGER NOT NULL NOT NULL, "last_active_at" INTEGER NOT NULL NOT NULL, "settings" TEXT, "info" TEXT, "oauth_sub" TEXT);
CREATE UNIQUE INDEX "user_api_key" ON "user" ("api_key");
CREATE UNIQUE INDEX "user_id" ON "user" ("id");
CREATE TABLE "memory" ("id" VARCHAR(255) NOT NULL, "user_id" VARCHAR(255) NOT NULL, "content" TEXT NOT NULL, "updated_at" INTEGER NOT NULL, "created_at" INTEGER NOT NULL);
CREATE UNIQUE INDEX "memory_id" ON "memory" ("id");
CREATE TABLE "model" ("id" TEXT NOT NULL, "user_id" TEXT NOT NULL, "base_model_id" TEXT, "name" TEXT NOT NULL, "meta" TEXT NOT NULL, "params" TEXT NOT NULL, "created_at" INTEGER NOT NULL, "updated_at" INTEGER NOT NULL);
CREATE UNIQUE INDEX "model_id" ON "model" ("id");
CREATE TABLE "tool" ("id" TEXT NOT NULL, "user_id" TEXT NOT NULL, "name" TEXT NOT NULL, "content" TEXT NOT NULL, "specs" TEXT NOT NULL, "meta" TEXT NOT NULL, "created_at" INTEGER NOT NULL, "updated_at" INTEGER NOT NULL, "valves" TEXT);
CREATE UNIQUE INDEX "tool_id" ON "tool" ("id");
CREATE TABLE "file" ("id" TEXT NOT NULL, "user_id" TEXT NOT NULL, "filename" TEXT NOT NULL, "meta" TEXT NOT NULL, "created_at" INTEGER NOT NULL);
CREATE UNIQUE INDEX "file_id" ON "file" ("id");
CREATE UNIQUE INDEX "user_oauth_sub" ON "user" ("oauth_sub");
CREATE TABLE "function" ("id" TEXT NOT NULL, "user_id" TEXT NOT NULL, "name" TEXT NOT NULL, "type" TEXT NOT NULL, "content" TEXT NOT NULL, "meta" TEXT NOT NULL, "created_at" INTEGER NOT NULL, "updated_at" INTEGER NOT NULL, "valves" TEXT, "is_active" INTEGER NOT NULL, "is_global" INTEGER NOT NULL);
CREATE UNIQUE INDEX "function_id" ON "function" ("id");
CREATE TABLE "chat_share" ("id" TEXT NOT NULL, "chat_id" TEXT NOT NULL, "shared_by" TEXT NOT NULL, "target_type" TEXT NOT NULL, "target_id" TEXT NOT NULL, "share_mode" TEXT NOT NULL, "snapshot_chat_id" TEXT, "created_at" INTEGER NOT NULL);
CREATE UNIQUE INDEX "chatshare_id" ON "chat_share" ("id");
