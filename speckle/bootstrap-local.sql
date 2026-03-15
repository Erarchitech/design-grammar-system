INSERT INTO scopes(name, description, public) VALUES
('workspace:create', 'Create workspaces', true),
('workspace:read', 'Read workspaces', true),
('workspace:update', 'Update workspaces', true),
('workspace:delete', 'Delete workspaces', true)
ON CONFLICT (name) DO NOTHING;

INSERT INTO server_apps_scopes("appId", "scopeName") VALUES
('spklwebapp', 'workspace:read'),
('explorer', 'workspace:read')
ON CONFLICT DO NOTHING;

INSERT INTO token_scopes("tokenId", "scopeName")
SELECT ust."tokenId", 'workspace:read'
FROM user_server_app_tokens ust
WHERE ust."appId" = 'spklwebapp'
ON CONFLICT DO NOTHING;
