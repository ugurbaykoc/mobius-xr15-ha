// Minimal custom Lovelace card: a colored slider bar for a number entity,
// using the native <input type="range"> with CSS accent-color so the bar
// itself is tinted to match the channel it controls. No dependencies, no
// build step.
//
// Usage in a dashboard:
//   type: custom:xr15-channel-bar-card
//   entity: number.xxxxxxxxxxxx_ch21
//   color: "#7c3aed"
//   name: UV   # optional, defaults to the entity's friendly name

class XR15ChannelBarCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("xr15-channel-bar-card: 'entity' is required");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const stateObj = hass.states[this._config.entity];
    if (!stateObj) return;

    if (this._title) {
      this._title.textContent = this._config.name || stateObj.attributes.friendly_name || this._config.entity;
    }

    const min = stateObj.attributes.min ?? 0;
    const max = stateObj.attributes.max ?? 1000;
    const step = stateObj.attributes.step ?? 10;
    if (this._input) {
      this._input.min = min;
      this._input.max = max;
      this._input.step = step;
      if (document.activeElement !== this._input) {
        this._input.value = stateObj.state;
      }
    }
    if (this._value) {
      this._value.textContent = stateObj.state;
    }
  }

  _render() {
    const color = this._config.color || "#3b82f6";
    this.innerHTML = `
      <ha-card>
        <div class="xr15-bar-content">
          <div class="xr15-bar-row">
            <span class="xr15-bar-title"></span>
            <span class="xr15-bar-value"></span>
          </div>
          <input type="range" class="xr15-bar-input" />
        </div>
      </ha-card>
      <style>
        ha-card {
          background: linear-gradient(135deg,#04101f,#071b33);
          color: white;
          border-radius: 16px;
          border: 1px solid rgba(80,160,255,.35);
          box-shadow: 0 0 15px rgba(0,120,255,.15);
        }
        .xr15-bar-content {
          padding: 10px 16px;
        }
        .xr15-bar-row {
          display: flex;
          justify-content: space-between;
          font-size: 13px;
          font-weight: bold;
          margin-bottom: 6px;
        }
        .xr15-bar-value {
          color: ${color};
        }
        .xr15-bar-input {
          width: 100%;
          height: 18px;
          accent-color: ${color};
        }
      </style>
    `;
    this._title = this.querySelector(".xr15-bar-title");
    this._value = this.querySelector(".xr15-bar-value");
    this._input = this.querySelector(".xr15-bar-input");

    this._input.addEventListener("input", () => {
      if (this._value) this._value.textContent = this._input.value;
    });
    this._input.addEventListener("change", () => {
      this._hass.callService("number", "set_value", {
        entity_id: this._config.entity,
        value: Number(this._input.value),
      });
    });

    if (this._hass) {
      this.hass = this._hass;
    }
  }

  getCardSize() {
    return 1;
  }

  static getStubConfig() {
    return { entity: "" };
  }
}

customElements.define("xr15-channel-bar-card", XR15ChannelBarCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "xr15-channel-bar-card",
  name: "XR15 Channel Bar",
  description: "A colored slider bar for a Mobius XR15 channel number entity.",
});
