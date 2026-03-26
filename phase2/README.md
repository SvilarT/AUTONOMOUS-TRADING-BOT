This `phase2` directory contains a refactored scaffold for the autonomous trading
bot.  The goal of this stage is to decouple the existing monolithic bot into
reusable components and lay the groundwork for plug‑in support.  Each module
defines clear interfaces and includes extensive docstrings to guide future
implementation.

Directories:

* **core/** – core services (data provider, strategy engine, execution router,
  risk manager, portfolio service).
* **plugins/** – example strategy and connector plugins.  Additional plugins
  can be dropped into this directory without modifying core code.
* **plugin_loader.py** – dynamic loader for discovering and instantiating
  plug‑ins based on configuration.
* **config.yml** – example configuration file specifying which strategies,
  connectors and settings to use.  In production this may be generated per
  user.
