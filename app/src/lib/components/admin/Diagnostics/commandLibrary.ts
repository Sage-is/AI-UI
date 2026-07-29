// Static catalog of 6 recovery snippets surfaced at the bottom of /admin/diagnostics.
//
// All entries are COPY-ONLY. The library never executes anything on the operator's
// behalf, by design. The previous diagnostic-page generation used an arbitrary-shell
// run surface; that was rejected as anti-poka-yoke. Operators paste these into their
// own terminal and run them under their own audit trail.
//
// Source: the Phase 0 recovery playbook in
// ~/.claude/plans/due-to-the-many-silly-ladybug.md (the Bonsai™ roadmap).

// The DATA lives in commandLibrary.json beside this file. Two readers need it
// now — this component and the server-rendered diagnostics page, which has no
// bundler to import a .ts through. Same reason as fixRegistry.json: a second
// hand-typed copy is the drift this migration exists to delete.
import commandLibraryData from './commandLibrary.json';

export interface CommandEntry {
	id: string;
	title_key: string; // i18n key
	description_key: string; // i18n key
	command: string;
	warning_key?: string; // optional i18n key for an inline warning (e.g. "never run when alembic_ahead")
}

export const commandLibrary: CommandEntry[] = commandLibraryData as CommandEntry[];
