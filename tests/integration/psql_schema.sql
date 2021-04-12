-- Drop all tables in the database
DO $$ DECLARE
	r RECORD;
BEGIN
	FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
		EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
	END LOOP;
END $$;

-- Create new ones

-- Lookup table for all workspaces. When any workspace is created, its wid is added here. userid is
-- optional. wtype can be 'individual', 'sharing', 'group', or 'alias'
CREATE TABLE workspaces(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL,
	uid VARCHAR(64), domain VARCHAR(255) NOT NULL, wtype VARCHAR(32) NOT NULL,
	status VARCHAR(16) NOT NULL, password VARCHAR(128));

CREATE TABLE aliases(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL, alias CHAR(292) NOT NULL);

-- passcodes table is used for password resets
CREATE TABLE passcodes(rowid SERIAL PRIMARY KEY, wid VARCHAR(36) NOT NULL UNIQUE,
	passcode VARCHAR(128) NOT NULL, expires TIMESTAMP NOT NULL);

-- For logging different types of failures, such as failed usernanme entry or a server's failure
-- to authenticate for delivery. Information stored here is to ensure that all parties which the
-- server interacts with behave themselves.
CREATE TABLE failure_log(rowid SERIAL PRIMARY KEY, type VARCHAR(16) NOT NULL,
	id VARCHAR(36), source VARCHAR(36) NOT NULL, count INTEGER,
	last_failure TIMESTAMP NOT NULL, lockout_until TIMESTAMP);

-- Preregistration information. Entries are removed upon successful account registration.
CREATE TABLE prereg(rowid SERIAL PRIMARY KEY, wid VARCHAR(36) NOT NULL UNIQUE,
	uid VARCHAR(128) NOT NULL, domain VARCHAR(255) NOT NULL, regcode VARCHAR(128));

-- Stores all entries in the keycard tree
CREATE TABLE keycards(rowid SERIAL PRIMARY KEY, owner VARCHAR(292) NOT NULL,
	creationtime TIMESTAMP NOT NULL, index INTEGER NOT NULL,
	entry VARCHAR(8192) NOT NULL, fingerprint VARCHAR(96) NOT NULL);

-- Keycard information for the organization
CREATE TABLE orgkeys(rowid SERIAL PRIMARY KEY, creationtime TIMESTAMP NOT NULL, 
	pubkey VARCHAR(7000), privkey VARCHAR(7000) NOT NULL, 
	purpose VARCHAR(8) NOT NULL, fingerprint VARCHAR(96) NOT NULL);

-- Disk quota tracking
CREATE TABLE quotas(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL, usage BIGINT, quota BIGINT);

-- For logging updates made to a workspace. This table is critical to device synchronization. The
-- update_data field is specific to the update type.
-- 
-- Update Types
-- 1: CREATE. An item has been created. update_data contains the path of the item created. Note
--    that this applies both to files and directories
-- 2: DELETE. An item has een deleted. update_data contains the path of the item created. Note
--    that this applies both to files and directories. If a directory has been deleted, all of
--	  its contents have also been deleted, which improves performance when large directories go
--    away.
-- 3: MOVE. An item has been moved. update_data contains two paths, the source and the destination.
--    The source path contains the directory path, and in the case of a file, the file name. The 
--    destination contains only a folder path.
-- 4: ROTATE. Keys have been rotated. update_data contains the path to the encrypted key storage
--    package.

CREATE TABLE updates(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL, update_type INTEGER,
	update_data VARCHAR(2048));

-- Information about individual workspaces

CREATE TABLE iwkspc_folders(rowid SERIAL PRIMARY KEY, wid char(36) NOT NULL, 
	enc_key VARCHAR(64) NOT NULL);

-- Devices registered to each individual's workspace
CREATE TABLE iwkspc_devices(rowid SERIAL PRIMARY KEY, wid CHAR(36) NOT NULL,
	devid CHAR(36) NOT NULL, devkey VARCHAR(1000) NOT NULL, status VARCHAR(16) NOT NULL);

