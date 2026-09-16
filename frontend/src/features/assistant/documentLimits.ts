/** Shared document intake limits (must match backend MAX_UPLOAD_BYTES default). */

function resolveMaxUploadBytes(): number {
  const raw = import.meta.env.VITE_MAX_UPLOAD_BYTES
  if (typeof raw === 'string' && raw.trim() !== '') {
    const parsed = Number(raw)
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed
    }
  }
  // Default matches backend Settings.MAX_UPLOAD_BYTES (4 MiB, Vercel-safe).
  return 4 * 1024 * 1024
}

export const MAX_UPLOAD_BYTES = resolveMaxUploadBytes()

export const SUPPORTED_DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.eml'] as const

export type SupportedDocumentExtension =
  (typeof SUPPORTED_DOCUMENT_EXTENSIONS)[number]

export const UNSUPPORTED_DOCUMENT_MESSAGE =
  'Unsupported document type. Choose a PDF, TXT, or EML complaint file.'

function uploadLimitMegabytes(): number {
  return Math.max(1, Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024)))
}

export const FILE_TOO_LARGE_MESSAGE = `Document exceeds the maximum upload size of ${uploadLimitMegabytes()} MB.`

export function documentExtension(filename: string): string {
  const trimmed = filename.trim()
  const dot = trimmed.lastIndexOf('.')
  if (dot < 0) {
    return ''
  }
  return trimmed.slice(dot).toLowerCase()
}

export function isSupportedDocumentFilename(filename: string): boolean {
  const extension = documentExtension(filename)
  return (SUPPORTED_DOCUMENT_EXTENSIONS as readonly string[]).includes(extension)
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function validateSelectedDocument(file: File): string | null {
  if (!isSupportedDocumentFilename(file.name)) {
    return UNSUPPORTED_DOCUMENT_MESSAGE
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return FILE_TOO_LARGE_MESSAGE
  }
  return null
}
