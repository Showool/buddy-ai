-- Table: public.user_files

-- DROP TABLE IF EXISTS public.user_files;

CREATE TABLE IF NOT EXISTS public.user_files
(
    id character varying(255) COLLATE pg_catalog."default" NOT NULL,
    user_id character varying(255) COLLATE pg_catalog."default" NOT NULL,
    original_filename character varying(255) COLLATE pg_catalog."default" NOT NULL,
    file_content bytea NOT NULL,
    file_type character varying(50) COLLATE pg_catalog."default" NOT NULL,
    file_size bigint NOT NULL,
    upload_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_public boolean DEFAULT false,
    content_hash character varying(64) COLLATE pg_catalog."default",
    document_summary text COLLATE pg_catalog."default",
    chunk_count integer DEFAULT 0,
    last_vectorized_at timestamp with time zone,
    vectorization_status character varying(50) COLLATE pg_catalog."default" DEFAULT 'pending'::character varying,
    CONSTRAINT user_files_pkey PRIMARY KEY (id),
    CONSTRAINT user_files_user_id_original_filename_key UNIQUE (user_id, original_filename)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_files
    OWNER to postgres;
-- Index: idx_user_files_user_id

-- DROP INDEX IF EXISTS public.idx_user_files_user_id;

CREATE INDEX IF NOT EXISTS idx_user_files_user_id
    ON public.user_files USING btree
    (user_id COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;