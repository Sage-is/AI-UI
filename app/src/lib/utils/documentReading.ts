// Before an upload starts, the composer and the knowledge page ask whether this
// box can read a document now (card "An upload starts before anyone checks that
// the box can read it", 2026-11-03). Without the rag-loaders, embedding or vector
// Sprigs an upload answered 200 with nothing extracted, and said so only after
// the wait. Now a member is told at once whom to ask, and an admin gets one
// button that runs the setup wizard's own install and shows it working.
import { toast } from 'svelte-sonner';
import { getDocumentReadiness, getModelsStatus, triggerModelDownload } from '$lib/apis/retrieval';

type Translate = (key: string, options?: Record<string, unknown>) => string;

const POLL_MS = 2000;
const LIMIT_MS = 15 * 60 * 1000; // a first embedding pull can take minutes

/** The AI Engine install the wizard runs: it grafts the loaders, the vector store and an embedding Sprig. */
const turnOn = async (t: Translate) => {
	const token = localStorage.token;
	await triggerModelDownload(token, { components: ['embedding'] });
	for (const started = Date.now(); Date.now() - started < LIMIT_MS; ) {
		await new Promise((done) => setTimeout(done, POLL_MS));
		const status = await getModelsStatus(token);
		if (status?.models?.error) throw new Error(status.models.error);
		if ((await getDocumentReadiness(token))?.ready) return;
	}
	throw new Error(t('Document reading is still turning on. Admin → Sprigs shows where it stands.'));
};

/** True when an upload may start; otherwise it says why, and offers an admin the fix. */
export const documentReadingReady = async (isAdmin: boolean, t: Translate): Promise<boolean> => {
	const readiness = await getDocumentReadiness(localStorage.token).catch(() => null);
	if (!readiness || readiness.ready) return true; // unknown: the upload itself reports
	if (!isAdmin) {
		toast.error(
			t('This box cannot read documents yet. Ask your admin to turn on document reading.')
		);
		return false;
	}
	toast.error(t('This box cannot read documents yet.'), {
		duration: 15000,
		action: {
			label: t('Turn on document reading'),
			onClick: () =>
				toast.promise(turnOn(t), {
					loading: t('Turning on document reading…'),
					success: t('Document reading is on. Add your file again.'),
					error: (e) => `${(e as Error)?.message ?? e}`
				})
		}
	});
	return false;
};
