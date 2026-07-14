#!/usr/bin/env bash
# 皇甫谧数字人文平台 — P0 启动/基线验证命令清单
# 后端、前端、Docker 必须已运行。
# 执行方式: bash scripts/p0-verify.sh

set -euo pipefail

# ---- helpers ----
_books()  { curl -sf "http://127.0.0.1:8000/api/v1/books" ${1:+-H "Authorization: Bearer $1"} | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'total={d[\"data\"][\"total\"]}')
for i in d['data']['items']:
    print(f'  {i[\"title\"]} ({i.get(\"dynasty\",\"?\")})')
"; }

_versions(){ curl -sf "http://127.0.0.1:8000/api/v1/versions" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'total={d[\"data\"][\"total\"]}')
for i in d['data']['items']:
    print(f'  {i[\"version_name\"]} ({i.get(\"era\",\"?\")})')
"; }

_passages(){ curl -sf "http://127.0.0.1:8000/api/v1/passages?limit=3" ${1:+-H "Authorization: Bearer $1"} | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'total={d[\"data\"][\"total\"]}')
for i in d['data']['items']:
    print(f'  {i[\"content_text\"][:60]}...')
"; }

_researcher_token() {
  curl -sf http://127.0.0.1:8000/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"researcher","password":"researcher123"}' \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])"
}

_me() {
  curl -sf http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer $1" \
    | python3 -c "
import sys,json
u=json.load(sys.stdin)['data']
print(f'  username={u[\"username\"]} display={u[\"display_name\"]} roles={[r[\"name\"] for r in u[\"roles\"]]}')
"
}

_sql() { PGPASSWORD=change-me psql -h 127.0.0.1 -U hfb -d hfb -q -t -c "$1" 2>&1; }

echo "=============================="
echo " P0 启动验证 — $(date '+%H:%M:%S')"
echo "=============================="

echo ""
echo "--- 1. Docker 服务 ---"
docker compose -f docker-compose.dev.yml ps --format 'table {{.Name}}\t{{.Status}}' 2>/dev/null || echo "(compose not in PATH)"

echo ""
echo "--- 2. /health ---"
curl -sS -w "HTTP %{http_code}\n" http://127.0.0.1:8000/health -o /dev/null

echo ""
echo "--- 3. /ready ---"
curl -sf http://127.0.0.1:8000/ready | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d['data']['services']
print(f'ready={d[\"data\"][\"ready\"]}  PG={s[\"PostgreSQL\"][\"healthy\"]} Redis={s[\"Redis\"][\"healthy\"]} ES={s[\"Elasticsearch\"][\"healthy\"]} MinIO={s[\"MinIO\"][\"healthy\"]}')
"

echo ""
echo "--- 4. Frontend :5173 ---"
curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:5173/

echo ""
echo "--- 5. /api/v1/books (anonymous) ---"
_books

echo ""
echo "--- 6. Anonymous POST /books (expected 401) ---"
curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/api/v1/books \
  -X POST -H 'Content-Type: application/json' -d '{"title":"test"}'

echo ""
echo "--- 7. Researcher login + /me ---"
TOKEN=$(_researcher_token)
echo "  login OK (token=${TOKEN:0:16}...)"
_me "$TOKEN"

echo ""
echo "--- 8. Researcher browse ---"
echo "  books:"
_books "$TOKEN" | head -4
echo "  versions:"
_versions
echo "  passages:"
_passages "$TOKEN"

echo ""
echo "--- 9. Researcher PATCH (update) ---"
BOOK_ID=$(curl -sf http://127.0.0.1:8000/api/v1/books | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['items'][0]['id'])")
curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/api/v1/books/$BOOK_ID \
  -X PATCH -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title_pinyin":"test-pinyin"}'

echo ""
echo "--- 10. DB counts ---"
_sql "SELECT 'users',count(*) FROM users WHERE is_deleted=false
UNION ALL SELECT 'roles',count(*) FROM roles WHERE is_deleted=false
UNION ALL SELECT 'books',count(*) FROM books WHERE is_deleted=false
UNION ALL SELECT 'versions',count(*) FROM versions WHERE is_deleted=false
UNION ALL SELECT 'passages',count(*) FROM passages WHERE is_deleted=false
UNION ALL SELECT 'chapters',count(*) FROM chapters WHERE is_deleted=false
UNION ALL SELECT 'documents',count(*) FROM documents WHERE is_deleted=false
UNION ALL SELECT 'chunks',count(*) FROM document_chunks WHERE is_deleted=false
UNION ALL SELECT 'evidences',count(*) FROM evidences WHERE is_deleted=false
UNION ALL SELECT 'citations',count(*) FROM citations WHERE is_deleted=false
UNION ALL SELECT 'entity_relations',count(*) FROM entity_relations WHERE is_deleted=false
ORDER BY 1;"

echo ""
echo "--- 11. Citation chain ---"
_sql "SELECT count(*) AS chains FROM citations c
JOIN evidences e ON c.evidence_id=e.id
JOIN passages p ON e.source_passage_id=p.id
JOIN versions v ON p.version_id=v.id
WHERE c.is_deleted=false AND e.is_deleted=false
  AND p.is_deleted=false AND v.is_deleted=false;"

echo ""
echo "--- 12. KG relations ---"
_sql "SELECT relation_type, source_entity_type, target_entity_type, evidence_status
FROM entity_relations WHERE is_deleted=false;"

echo ""
echo "--- 13. Multi-version ---"
_sql "SELECT v.version_name, v.era, count(p.id) AS passages
FROM versions v LEFT JOIN passages p ON p.version_id=v.id AND p.is_deleted=false
WHERE v.is_deleted=false GROUP BY v.id ORDER BY v.era;"

echo ""
echo "--- 14. SourceRefs (Codex: real PDF refs) ---"
_sql "SELECT count(*) AS source_refs FROM source_refs WHERE is_deleted=false;"
_sql "SELECT id, title, substring(url,1,80) AS url FROM source_refs WHERE is_deleted=false AND url LIKE 'https://%' LIMIT 3;"

echo ""
echo "--- 15. Page numbers (Codex: PDF page tracking) ---"
_sql "SELECT page_number, count(*) AS chunks FROM document_chunks WHERE is_deleted=false AND page_number IS NOT NULL GROUP BY page_number ORDER BY page_number LIMIT 10;"

echo ""
echo "--- 16. PDF documents ---"
_sql "SELECT id, title, substring(source_url,1,80) AS source_url, length(raw_pdf_blob) AS pdf_bytes, substring(content_checksum,1,16) AS checksum FROM documents WHERE raw_pdf_blob IS NOT NULL AND is_deleted=false;"

echo ""
echo "--- 17. Full evidence chain (Codex: 5 auditable facts) ---"
_sql "SELECT er.relation_type, er.claim_text, dc.page_number, substring(er.evidence_source_uri,1,60) AS source_uri
FROM entity_relations er
LEFT JOIN document_chunks dc ON er.evidence_chunk_id = dc.id AND dc.is_deleted=false
WHERE er.is_deleted=false AND er.evidence_status='verified'
  AND er.evidence_document_id IS NOT NULL
LIMIT 5;"

echo ""
echo "--- 18. Academic RAG probe ---"
TOKEN=$(_researcher_token)
curl -sf http://127.0.0.1:8000/api/v1/academic-rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"《针灸甲乙经》的成书特点是什么？"}' \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)['data']
print(f'refusal={d[\"refusal\"]} citations={len(d[\"citations\"])} kg_paths={len(d[\"kg_paths\"])}')
for i,c in enumerate(d['citations'][:5]):
    print(f'  [{i+1}] doc={c[\"document_id\"][:16]}... chunk={c[\"chunk_id\"][:16]}... quote={c[\"exact_quote\"][:60]}...')
"

echo ""
echo "=============================="
echo " 验证完成"
echo "=============================="
