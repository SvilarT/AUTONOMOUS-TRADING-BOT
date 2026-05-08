// webpack-health-plugin.js
// Webpack plugin that tracks compilation state and health metrics
// Enhanced with proper memory management, event emission, and detailed tracking

const EventEmitter = require('events');

/**
 * Configuration for the health plugin
 */
const PLUGIN_CONFIG = {
  maxErrorsStored: 50, // Keep last 50 errors
  maxWarningsStored: 100, // Keep last 100 warnings
  compileTimeWindow: 3600000, // Track compile times within 1 hour
};

/**
 * WebpackHealthPlugin - Production-grade compilation monitoring
 * Extends EventEmitter to allow external subscribers
 */
class WebpackHealthPlugin extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = { ...PLUGIN_CONFIG, ...config };

    this.status = {
      state: 'idle', // idle, compiling, success, failed
      errors: [],
      warnings: [],
      lastCompileTime: null,
      lastSuccessTime: null,
      compileDuration: 0,
      totalCompiles: 0,
      firstCompileTime: null,
      totalCompileDuration: 0, // NEW: Track total compile time
      buildCount: {
        success: 0,
        failed: 0,
      },
    };

    // Historical data for trends
    this.history = {
      compileTimes: [], // Array of compile durations for averaging
      stateChanges: [], // Timeline of state transitions
    };

    this._isCompiling = false;
    this._currentCompileStart = null;
  }

  /**
   * Apply plugin to webpack compiler
   */
  apply(compiler) {
    const pluginName = 'WebpackHealthPlugin';

    // Hook: Compilation started
    compiler.hooks.compile.tap(pluginName, () => {
      const now = Date.now();

      // Prevent double-compilation
      if (this._isCompiling) {
        console.warn('[WebpackHealthPlugin] Compile hook fired while already compiling');
        return;
      }

      this._isCompiling = true;
      this._currentCompileStart = now;

      this.status.state = 'compiling';
      this.status.lastCompileTime = now;

      if (!this.status.firstCompileTime) {
        this.status.firstCompileTime = now;
      }

      this._recordStateChange('compiling');
      this.emit('compile:start', { timestamp: now });
    });

    // Hook: Compilation completed
    compiler.hooks.done.tap(pluginName, (stats) => {
      if (!this._isCompiling || !this._currentCompileStart) {
        console.warn('[WebpackHealthPlugin] Done hook fired without matching compile start');
        return;
      }

      const compileDuration = Date.now() - this._currentCompileStart;
      this._isCompiling = false;

      // Update core metrics
      this.status.compileDuration = compileDuration;
      this.status.totalCompiles++;
      this.status.totalCompileDuration += compileDuration;

      // Track compile time for averaging
      this._recordCompileTime(compileDuration);

      // Extract error and warning info
      const info = stats.toJson({
        all: false,
        errors: true,
        warnings: true,
      });

      // Process errors
      if (stats.hasErrors()) {
        this.status.state = 'failed';
        this.status.buildCount.failed++;

        const errors = info.errors.map((err) => ({
          message: err.message || String(err),
          stack: err.stack || null,
          moduleName: err.moduleName || null,
          loc: err.loc || null,
          severity: 'error',
          timestamp: Date.now(),
        }));

        this.status.errors = this._mergeWithLimit(
          this.status.errors,
          errors,
          this.config.maxErrorsStored
        );
      } else {
        this.status.state = 'success';
        this.status.buildCount.success++;
        this.status.lastSuccessTime = Date.now();
        this.status.errors = [];
      }

      // Process warnings
      if (stats.hasWarnings()) {
        const warnings = info.warnings.map((warn) => ({
          message: warn.message || String(warn),
          moduleName: warn.moduleName || null,
          loc: warn.loc || null,
          severity: 'warning',
          timestamp: Date.now(),
        }));

        this.status.warnings = this._mergeWithLimit(
          this.status.warnings,
          warnings,
          this.config.maxWarningsStored
        );
      } else {
        this.status.warnings = [];
      }

      this._recordStateChange(this.status.state);
      this.emit('compile:done', {
        state: this.status.state,
        duration: compileDuration,
        errorCount: this.status.errors.length,
        warningCount: this.status.warnings.length,
        timestamp: Date.now(),
      });
    });

    // Hook: Compilation failed (catastrophic failure)
    compiler.hooks.failed.tap(pluginName, (error) => {
      this._isCompiling = false;

      const compileDuration = this._currentCompileStart
        ? Date.now() - this._currentCompileStart
        : 0;

      this.status.state = 'failed';
      this.status.buildCount.failed++;
      this.status.compileDuration = compileDuration;
      this.status.totalCompiles++;
      this.status.totalCompileDuration += compileDuration;

      this.status.errors = [
        {
          message: error.message || 'Unknown error',
          stack: error.stack || null,
          severity: 'fatal',
          timestamp: Date.now(),
        },
      ];

      this._recordStateChange('failed');
      this._recordCompileTime(compileDuration);

      this.emit('compile:failed', {
        error: error.message,
        duration: compileDuration,
        timestamp: Date.now(),
      });
    });

    // Hook: Invalid (file changed, recompiling)
    compiler.hooks.invalid.tap(pluginName, (fileName) => {
      this.status.state = 'compiling';
      this._recordStateChange('compiling');

      this.emit('compile:invalid', {
        fileName,
        timestamp: Date.now(),
      });
    });
  }

  /**
   * Get full status object with all computed fields
   */
  getStatus() {
    const avgCompileTime = this._getAverageCompileTime();

    return {
      ...this.status,
      // Computed fields
      isHealthy: this.status.state === 'success',
      errorCount: this.status.errors.length,
      warningCount: this.status.warnings.length,
      hasCompiled: this.status.totalCompiles > 0,
      averageCompileTime: avgCompileTime,
      successRate:
        this.status.totalCompiles > 0
          ? Math.round(
              (this.status.buildCount.success / this.status.totalCompiles) * 100
            )
          : null,
      // Add history summary
      history: {
        recentCompileTimes: this.history.compileTimes.slice(-10), // Last 10
        stateChangeCount: this.history.stateChanges.length,
      },
    };
  }

  /**
   * Get simplified status for quick checks
   */
  getSimpleStatus() {
    return {
      state: this.status.state,
      isHealthy: this.status.state === 'success',
      errorCount: this.status.errors.length,
      warningCount: this.status.warnings.length,
      lastCompileTime: this.status.lastCompileTime,
      compileDuration: this.status.compileDuration,
    };
  }

  /**
   * Reset all statistics (useful for testing)
   */
  reset() {
    this.status = {
      state: 'idle',
      errors: [],
      warnings: [],
      lastCompileTime: null,
      lastSuccessTime: null,
      compileDuration: 0,
      totalCompiles: 0,
      firstCompileTime: null,
      totalCompileDuration: 0,
      buildCount: {
        success: 0,
        failed: 0,
      },
    };

    this.history = {
      compileTimes: [],
      stateChanges: [],
    };

    this._isCompiling = false;
    this._currentCompileStart = null;

    this.emit('reset', { timestamp: Date.now() });
  }

  /**
   * PRIVATE: Record compile time for historical tracking
   */
  _recordCompileTime(duration) {
    this.history.compileTimes.push({
      duration,
      timestamp: Date.now(),
    });

    // Cleanup old entries (keep last hour)
    const cutoff = Date.now() - this.config.compileTimeWindow;
    this.history.compileTimes = this.history.compileTimes.filter(
      (entry) => entry.timestamp > cutoff
    );
  }

  /**
   * PRIVATE: Record state transitions for diagnostics
   */
  _recordStateChange(newState) {
    this.history.stateChanges.push({
      state: newState,
      timestamp: Date.now(),
    });

    // Keep only last 100 state changes
    if (this.history.stateChanges.length > 100) {
      this.history.stateChanges.shift();
    }
  }

  /**
   * PRIVATE: Merge new errors/warnings, maintaining limit
   */
  _mergeWithLimit(existing, newItems, limit) {
    const merged = [...existing, ...newItems];
    if (merged.length > limit) {
      return merged.slice(merged.length - limit); // Keep most recent
    }
    return merged;
  }

  /**
   * PRIVATE: Calculate average compile time
   */
  _getAverageCompileTime() {
    if (this.history.compileTimes.length === 0) return null;

    const total = this.history.compileTimes.reduce((sum, entry) => sum + entry.duration, 0);
    return Math.round(total / this.history.compileTimes.length);
  }
}

module.exports = WebpackHealthPlugin;
