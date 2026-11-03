from pokemon.battle import damage


def test_admin_notification_import_errors_are_nonfatal(monkeypatch):
	def fail_import(_path):
		raise RuntimeError("settings are not configured")

	monkeypatch.setattr(damage, "safe_import", fail_import)

	damage._notify_admins("Move raw data missing basePower")
