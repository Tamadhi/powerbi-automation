from pbi_automation.settings import load_fabric_settings, repo_root_from


def test_fabric_settings_use_provided_workspace() -> None:
    root = repo_root_from()
    settings = load_fabric_settings(root)
    assert settings.workspace_id == "9cff40b2-3355-4759-998a-7b469fa922f6"
    assert "9cff40b2-3355-4759-998a-7b469fa922f6" in settings.workspace_open_url
    assert settings.git_folder == "workspace"
    assert settings.github_repo == "Tamadhi/powerbi_automation"
