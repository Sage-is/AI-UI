// Static catalog of 6 recovery snippets surfaced at the bottom of /admin/diagnostics.
//
// All entries are COPY-ONLY. The library never executes anything on the operator's
// behalf, by design. The previous diagnostic-page generation used an arbitrary-shell
// run surface; that was rejected as anti-poka-yoke. Operators paste these into their
// own terminal and run them under their own audit trail.
//
// Source: the Phase 0 recovery playbook in
// ~/.claude/plans/due-to-the-many-silly-ladybug.md (the Bonsai™ roadmap).

export interface CommandEntry {
	id: string;
	title_key: string; // i18n key
	description_key: string; // i18n key
	command: string;
	warning_key?: string; // optional i18n key for an inline warning (e.g. "never run when alembic_ahead")
}

export const commandLibrary: CommandEntry[] = [
	{
		id: 'sqlite_open',
		title_key: 'diagnostics.library.sqlite_open.title',
		description_key: 'diagnostics.library.sqlite_open.description',
		command: [
			'# 1. Get a shell inside the running container',
			'docker exec -it srv-captain--<app-name> bash',
			'',
			'# 2. Inside the container, open the SQLite database',
			'sqlite3 /app/backend/data/webui.db',
			'',
			'# 3. (optional) set output formatting',
			'.headers on',
			'.mode column'
		].join('\n')
	},

	{
		id: 'inspect_stale_openai_urls',
		title_key: 'diagnostics.library.inspect_stale_openai_urls.title',
		description_key: 'diagnostics.library.inspect_stale_openai_urls.description',
		command:
			"SELECT id, data FROM config WHERE data LIKE '%OPENAI_API_BASE_URLS%' ORDER BY id DESC LIMIT 5;"
	},

	{
		id: 'inspect_stale_ollama_urls',
		title_key: 'diagnostics.library.inspect_stale_ollama_urls.title',
		description_key: 'diagnostics.library.inspect_stale_ollama_urls.description',
		command:
			"SELECT id, data FROM config WHERE data LIKE '%OLLAMA_BASE_URLS%' ORDER BY id DESC LIMIT 5;"
	},

	{
		id: 'generate_secret_key',
		title_key: 'diagnostics.library.generate_secret_key.title',
		description_key: 'diagnostics.library.generate_secret_key.description',
		command: 'head -c 32 /dev/random | base64'
	},

	{
		id: 'run_pending_migrations',
		title_key: 'diagnostics.library.run_pending_migrations.title',
		description_key: 'diagnostics.library.run_pending_migrations.description',
		command: 'cd /app/backend && alembic upgrade head',
		warning_key: 'diagnostics.library.run_pending_migrations.warning'
	},

	{
		id: 'restart_container',
		title_key: 'diagnostics.library.restart_container.title',
		description_key: 'diagnostics.library.restart_container.description',
		command: 'docker restart srv-captain--<app-name>'
	}
];
