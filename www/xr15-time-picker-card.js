// Minimal custom Lovelace card wrapping the browser's native <input type="time">
// for an input_datetime entity. On iOS Safari this renders as the native
// scrolling wheel time picker; other browsers fall back to their own
// built-in time control (a plain box on desktop Chrome, a clock dial on
// Android). No external dependencies, no build step.
//
// Usage in a dashboard:
//   type: custom:xr15-time-picker-card
//   entity: input_datetime.radion_xr15_acilis_saati
//   name: Açılış Saati   # optional, defaults to the entity's friendly name

class XR15TimePickerCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("xr15-time-picker-card: 'entity' is required");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];
    if (!stateObj) return;

    if (this._title) {
      this._title.textContent =
        this._config.name || stateObj.attributes.friendly_name || this._config.entity;
    }

    const time = (stateObj.state || "00:00:00").slice(0, 5);
    if (this._input && document.activeElement !== this._input && this._input.value !== time) {
      this._input.value = time;
    }
  }

  _render() {
    this.innerHTML = `
      <ha-card>
        <div class="xr15-tp-content">
          <div class="xr15-tp-title"></div>
          <input type="time" class="xr15-tp-input" />
        </div>
      </ha-card>
      <style>
        ha-card {
          background: linear-gradient(135deg,#04101f,#071b33);
          color: white;
          border-radius: 22px;
          border: 1px solid rgba(80,160,255,.35);
          box-shadow: 0 0 25px rgba(0,120,255,.20);
        }
        .xr15-tp-content {
          padding: 16px 18px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
        }
        .xr15-tp-title {
          font-size: 15px;
          font-weight: bold;
          color: white;
        }
        .xr15-tp-input {
          font-size: 28px;
          padding: 8px 14px;
          border-radius: 12px;
          border: 1px solid rgba(80,160,255,.5);
          background: #0f2942;
          color: white;
          color-scheme: dark;
          width: 150px;
          text-align: center;
        }
      </style>
    `;
    this._title = this.querySelector(".xr15-tp-title");
    this._input = this.querySelector(".xr15-tp-input");
    this._input.addEventListener("change", (ev) => {
      const value = ev.target.value; // "HH:MM"
      if (!value) return;
      this._hass.callService("input_datetime", "set_datetime", {
        entity_id: this._config.entity,
        time: `${value}:00`,
      });
    });

    if (this._hass) {
      this.hass = this._hass;
    }
  }

  getCardSize() {
    return 2;
  }

  static getConfigElement() {
    return null;
  }

  static getStubConfig() {
    return { entity: "" };
  }
}

customElements.define("xr15-time-picker-card", XR15TimePickerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "xr15-time-picker-card",
  name: "XR15 Time Picker",
  description: "Native time input (wheel on iOS Safari) for an input_datetime entity.",
});
