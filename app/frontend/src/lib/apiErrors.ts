export type ParsedApiError = {
	message: string;
	code: string;
	status: number;
};

export function parseApiErrorBody(body: unknown, fallback: string, status: number): ParsedApiError {
	if (body && typeof body === 'object') {
		const record = body as Record<string, unknown>;
		const err = record.error;
		if (err && typeof err === 'object') {
			const e = err as { message?: string; code?: string };
			return {
				message: e.message || fallback,
				code: e.code || 'UNKNOWN',
				status
			};
		}
		if (typeof record.detail === 'string') {
			return { message: record.detail, code: 'HTTP_ERROR', status };
		}
	}
	return { message: fallback, code: 'HTTP_ERROR', status };
}

export class ApiClientError extends Error {
	readonly code: string;
	readonly status: number;

	constructor(parsed: ParsedApiError) {
		super(`${parsed.message} (${parsed.status})`);
		this.name = 'ApiClientError';
		this.code = parsed.code;
		this.status = parsed.status;
	}
}
