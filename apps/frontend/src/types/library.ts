/** Shared Library types for the Research Library module. */

/** Document brief — list view item mapped from GET /api/v1/documents */
export interface LibraryDocument {
    id: string;
    title: string;
    title_pinyin?: string | null;
    title_english?: string | null;
    dynasty?: string | null;
    category?: string | null;
    author_id?: string | null;
    copyright_status: string;
    review_status: string;
    rag_enabled: boolean;
    source_name?: string | null;
    withdrawn_at?: string | null;
    created_at?: string | null;
}

/** Document detail — full document from GET /api/v1/documents/{id} */
export interface LibraryDocumentDetail {
    id: string;
    title: string;
    title_pinyin?: string | null;
    title_english?: string | null;
    dynasty?: string | null;
    year?: number | null;
    category?: string | null;
    abstract?: string | null;
    content_text?: string | null;
    source_url?: string | null;
    page_count?: number | null;
    language: string;
    copyright_status: string;
    license_type?: string | null;
    authorization_basis?: string | null;
    review_status: string;
    reviewed_by?: string | null;
    reviewed_at?: string | null;
    rag_enabled: boolean;
    content_checksum?: string | null;
    source_name?: string | null;
    withdrawn_at?: string | null;
    withdraw_reason?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
}

/** Document stats from GET /api/v1/documents/{id}/stats */
export interface LibraryDocumentStats {
    total_chunks: number;
    ocr_chunks: number;
    ocr_text_available: boolean;
    avg_ocr_confidence?: number | null;
    citation_count: number;
    evidence_count: number;
}

/** Filter state for the library list */
export interface LibraryFilters {
    query: string;
    copyrightStatus: string;
    reviewStatus: string;
    dynasty: string;
    category: string;
    sourceName: string;
}

export const COPYRIGHT_STATUSES = [
    'public_domain',
    'open_access',
    'licensed',
    'user_uploaded_with_permission',
    'unknown',
    'metadata_only',
    'forbidden_fulltext',
    'commercial_restricted',
    'pirated',
] as const;

export const COPYRIGHT_LABELS: Record<string, string> = {
    public_domain: '公共领域',
    open_access: '开放获取',
    licensed: '已授权',
    user_uploaded_with_permission: '用户上传(已授权)',
    unknown: '未知',
    metadata_only: '仅元数据',
    forbidden_fulltext: '禁止全文',
    commercial_restricted: '商业限制',
    pirated: '盗版',
};

export const REVIEW_STATUSES = [
    'pending_review',
    'under_review',
    'approved',
    'rejected',
] as const;

export const REVIEW_LABELS: Record<string, string> = {
    pending_review: '待审核',
    under_review: '审核中',
    approved: '已通过',
    rejected: '已驳回',
};
