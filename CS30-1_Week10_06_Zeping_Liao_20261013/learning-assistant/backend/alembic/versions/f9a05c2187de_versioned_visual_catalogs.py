"""Retain legacy visual sources beside independently reviewed catalog versions."""

from alembic import op
import sqlalchemy as sa

revision = "f9a05c2187de"
down_revision = "f8e94fb071c0"
branch_labels = None
depends_on = None


def _audit():
    return [sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False)]


def upgrade():
    op.create_table(
        "visual_catalog_versions", *_audit(),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("importer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        *[sa.Column(name, sa.String(64), nullable=False) for name in ("source_sha256", "catalog_sha256", "manifest_sha256", "previous_catalog_sha256", "configuration_sha256")],
        sa.Column("extractor_revision", sa.String(80), nullable=False),
        sa.Column("catalog_schema", sa.String(80), nullable=False),
        sa.Column("artifact_manifest", sa.JSON(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.UniqueConstraint("document_version_id", "extractor_revision", "catalog_sha256"),
        sa.CheckConstraint("state IN ('staged','under_review','active','withdrawn')", name="ck_visual_catalog_state"),
    )
    op.create_table(
        "visual_catalog_candidates", *_audit(),
        sa.Column("catalog_id", sa.String(36), sa.ForeignKey("visual_catalog_versions.id"), nullable=False),
        sa.Column("region_id", sa.String(64), nullable=False),
        sa.Column("previous_region_id", sa.String(64), sa.ForeignKey("visual_regions.id"), nullable=False),
        sa.Column("physical_page", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("candidate_status", sa.String(40), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("catalog_id", "region_id"),
        sa.UniqueConstraint("catalog_id", "previous_region_id"),
    )
    op.create_table(
        "visual_catalog_reviews", *_audit(),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("visual_catalog_candidates.id"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_review_id", sa.String(36), sa.ForeignKey("visual_catalog_reviews.id"), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('accepted','rejected','needs_more')", name="ck_visual_catalog_review_decision"),
        sa.CheckConstraint("method = 'independent_human'", name="ck_visual_catalog_review_method"),
    )
    for table, names in {"visual_catalog_versions": ("workspace_id", "document_version_id"), "visual_catalog_candidates": ("catalog_id", "region_id", "previous_region_id"), "visual_catalog_reviews": ("candidate_id",)}.items():
        for name in names:
            op.create_index(f"ix_{table}_{name}", table, [name])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION guard_visual_catalog_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          RAISE EXCEPTION 'Visual catalog candidates and reviews are immutable'; END $$""")
        for table in ("visual_catalog_candidates", "visual_catalog_reviews"):
            op.execute(f"CREATE TRIGGER guard_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION guard_visual_catalog_immutable()")
        op.execute("""CREATE FUNCTION guard_visual_catalog_identity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Visual catalog history is retained'; END IF;
          IF TG_OP = 'INSERT' THEN
            IF NEW.state <> 'staged' THEN RAISE EXCEPTION 'Visual catalogs start staged'; END IF;
            IF NOT EXISTS (SELECT 1 FROM document_versions v JOIN documents d ON d.id=v.document_id
              JOIN users owner ON owner.id=d.owner_id JOIN users importer ON importer.id=NEW.importer_id JOIN roles r ON r.id=importer.role_id
              WHERE v.id=NEW.document_version_id AND v.raw_hash=NEW.source_sha256 AND owner.workspace_id=NEW.workspace_id
              AND importer.workspace_id=NEW.workspace_id AND importer.status='active' AND r.name='admin' AND d.active AND NOT d.revoked)
            THEN RAISE EXCEPTION 'Visual catalog owner or current source is invalid'; END IF;
            RETURN NEW;
          END IF;
          IF (to_jsonb(OLD) - ARRAY['state','version','updated_at']) IS DISTINCT FROM (to_jsonb(NEW) - ARRAY['state','version','updated_at']) THEN
            RAISE EXCEPTION 'Visual catalog identity is immutable'; END IF;
          IF NEW.version <> OLD.version+1 THEN RAISE EXCEPTION 'Visual catalog version must advance exactly once'; END IF;
          IF NEW.state <> OLD.state AND NOT ((OLD.state='staged' AND NEW.state IN ('under_review','withdrawn'))
            OR (OLD.state='under_review' AND NEW.state IN ('active','withdrawn')) OR (OLD.state='active' AND NEW.state='withdrawn'))
          THEN RAISE EXCEPTION 'Visual catalog state transition is invalid'; END IF;
          IF NEW.state='active' AND OLD.state <> 'active' THEN
            IF NOT EXISTS (SELECT 1 FROM document_versions v JOIN documents d ON d.id=v.document_id
              WHERE v.id=NEW.document_version_id AND v.raw_hash=NEW.source_sha256 AND d.active AND NOT d.revoked)
            THEN RAISE EXCEPTION 'Visual source is unavailable'; END IF;
            IF NOT EXISTS (SELECT 1 FROM visual_catalog_candidates c JOIN visual_catalog_reviews r ON r.candidate_id=c.id
              WHERE c.catalog_id=NEW.id AND r.decision='accepted' AND r.method='independent_human' AND r.reviewer_id<>NEW.importer_id
              AND r.payload_sha256=c.payload_sha256 AND NOT EXISTS (SELECT 1 FROM visual_catalog_reviews n
                WHERE n.candidate_id=c.id AND (n.reviewed_at,n.id)>(r.reviewed_at,r.id)))
            THEN RAISE EXCEPTION 'Independent accepted content is required for activation'; END IF;
          END IF;
          RETURN NEW; END $$""")
        op.execute("CREATE TRIGGER guard_visual_catalog_version_identity BEFORE INSERT OR UPDATE OR DELETE ON visual_catalog_versions FOR EACH ROW EXECUTE FUNCTION guard_visual_catalog_identity()")
        op.execute("""CREATE FUNCTION guard_visual_catalog_candidate_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM visual_catalog_versions v JOIN visual_regions legacy_region ON legacy_region.id=NEW.previous_region_id
            WHERE v.id=NEW.catalog_id AND v.state='staged' AND legacy_region.document_version_id=v.document_version_id
            AND legacy_region.catalog_sha256=v.previous_catalog_sha256 AND legacy_region.physical_page=NEW.physical_page AND legacy_region.kind=NEW.kind
            AND NEW.raw_payload::jsonb->>'source_sha256'=v.source_sha256 AND NEW.raw_payload::jsonb->>'extractor_revision'=v.extractor_revision
            AND NEW.raw_payload::jsonb->>'region_id'=NEW.region_id AND NEW.raw_payload::jsonb->>'kind'=NEW.kind
            AND NEW.raw_payload::jsonb->>'status'=NEW.candidate_status AND (NEW.raw_payload::jsonb->>'physical_pdf_page')::integer=NEW.physical_page
            AND NEW.raw_payload::jsonb->'details'->>'previous_region_id'=NEW.previous_region_id
            AND NEW.candidate_status=CASE NEW.kind WHEN 'table_candidate' THEN 'needs_structure_review' WHEN 'figure_image' THEN 'needs_visual_review' WHEN 'formula_candidate' THEN 'needs_formula_review' END)
          THEN RAISE EXCEPTION 'Visual candidate source lineage or staged state is invalid'; END IF;
          RETURN NEW; END $$""")
        op.execute("CREATE TRIGGER guard_visual_catalog_candidate_insert BEFORE INSERT ON visual_catalog_candidates FOR EACH ROW EXECUTE FUNCTION guard_visual_catalog_candidate_insert()")
        op.execute("""CREATE FUNCTION guard_visual_catalog_review_insert() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE prior text; BEGIN
          PERFORM 1 FROM visual_catalog_versions WHERE id=(SELECT catalog_id FROM visual_catalog_candidates WHERE id=NEW.candidate_id) FOR UPDATE;
          IF NOT EXISTS (SELECT 1 FROM visual_catalog_candidates c JOIN visual_catalog_versions v ON v.id=c.catalog_id
            JOIN document_versions original ON original.id=v.document_version_id JOIN documents d ON d.id=original.document_id
            JOIN users reviewer ON reviewer.id=NEW.reviewer_id JOIN roles role ON role.id=reviewer.role_id
            WHERE c.id=NEW.candidate_id AND v.state='under_review' AND NEW.reviewer_id<>v.importer_id
            AND reviewer.workspace_id=v.workspace_id AND reviewer.status='active' AND role.name='admin'
            AND original.raw_hash=v.source_sha256 AND d.active AND NOT d.revoked AND NEW.payload_sha256=c.payload_sha256)
          THEN RAISE EXCEPTION 'Independent reviewer or current candidate source is invalid'; END IF;
          SELECT id INTO prior FROM visual_catalog_reviews WHERE candidate_id=NEW.candidate_id ORDER BY reviewed_at DESC,id DESC LIMIT 1;
          IF prior IS DISTINCT FROM NEW.previous_review_id THEN RAISE EXCEPTION 'Visual review compare and swap failed'; END IF;
          IF NEW.decision='accepted' THEN
            IF NEW.checks::jsonb <> jsonb_build_object('source_page_match',true,'geometry_correct',true,'native_text_correct',true,'reading_order_correct',true,'content_correct',true,'notation_units_correct',true)
            THEN RAISE EXCEPTION 'All independent source checks must pass'; END IF;
            IF EXISTS (SELECT 1 FROM visual_catalog_candidates c WHERE c.id=NEW.candidate_id AND c.kind='table_candidate'
              AND (COALESCE((c.raw_payload::jsonb->'details'->>'rows')::integer,0)<=0 OR COALESCE((c.raw_payload::jsonb->'details'->>'columns')::integer,0)<=0
              OR jsonb_array_length(c.raw_payload::jsonb->'details'->'cells')<>(c.raw_payload::jsonb->'details'->>'rows')::integer
              OR EXISTS (SELECT 1 FROM jsonb_array_elements(c.raw_payload::jsonb->'details'->'cells') line
                WHERE jsonb_array_length(line)<>(c.raw_payload::jsonb->'details'->>'columns')::integer)))
            THEN RAISE EXCEPTION 'A complete table structure is required'; END IF;
          END IF;
          RETURN NEW; END $$""")
        op.execute("CREATE TRIGGER guard_visual_catalog_review_insert BEFORE INSERT ON visual_catalog_reviews FOR EACH ROW EXECUTE FUNCTION guard_visual_catalog_review_insert()")


def downgrade():
    bind = op.get_bind()
    if any(bind.scalar(sa.text(f"SELECT count(*) FROM {table}")) for table in ("visual_catalog_versions", "visual_catalog_candidates", "visual_catalog_reviews")):
        raise RuntimeError("Preserve all visual catalog versions, candidates and reviews before downgrade.")
    for table in ("visual_catalog_reviews", "visual_catalog_candidates", "visual_catalog_versions"):
        op.drop_table(table)
    if bind.dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_visual_catalog_immutable()")
        op.execute("DROP FUNCTION guard_visual_catalog_identity()")
        op.execute("DROP FUNCTION guard_visual_catalog_candidate_insert()")
        op.execute("DROP FUNCTION guard_visual_catalog_review_insert()")
