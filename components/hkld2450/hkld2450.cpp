#include "hkld2450.h"

namespace esphome {
namespace hkld2450 {

static const char* TAG = "hkld2450";

void HKLD2450::setup() {
    static const uint8_t MULTI_CMD[] = { 0x02,0x00,0x90,0x00,0x04,0x03,0x02,0x01 };
    send_command(MULTI_CMD, sizeof(MULTI_CMD));
    
    static const uint8_t BT_ON_CMD[] = { 0x04, 0x00, 0xA4, 0x00, 0x01, 0x00, 0x04, 0x03, 0x02, 0x01 };
    static const uint8_t BT_OFF_CMD[] = { 0x04, 0x00, 0xA4, 0x00, 0x00, 0x00, 0x04, 0x03, 0x02, 0x01 };
    if (this->bluetooth_)
        send_command(BT_ON_CMD, sizeof(BT_ON_CMD));
    else
        send_command(BT_OFF_CMD, sizeof(BT_OFF_CMD));
    
    static const uint8_t RESTART_CMD[] = { 0x02,0x00,0xA3,0x00,0x04,0x03,0x02,0x01 };
    send_command(RESTART_CMD, sizeof(RESTART_CMD));
}

void HKLD2450::update() {
    for(int t = 0; t < 3; ++t) {
        if ((this->zone_[t] != -1) || (t == 0)) {
            ESP_LOGD(TAG, "update() [%d][%d] - (%d x %d) -> %d (%d)", t, this->zone_[t], this->x_[t], this->y_[t], this->sp_[t], this->res_[t]);
        }
    }
    this->send_event_data();
}

void HKLD2450::loop() {
    while (available()) {
        int c = read();
        if (c < 0) break;
        if (this->input_pos < INPUT_BUF_SIZE) 
            this->input_buf[this->input_pos++] = static_cast<uint8_t>(c);
        else
            this->input_pos = 0;

        if (this->input_pos >= 10 
                && this->input_buf[this->input_pos-4]==0x04 
                && this->input_buf[this->input_pos-3]==0x03 
                && this->input_buf[this->input_pos-2]==0x02 
                && this->input_buf[this->input_pos-1]==0x01) {
            handle_ack_data(this->input_buf, this->input_pos);
            this->input_pos = 0;
            continue;
        }

        if (this->input_pos >= 30 
                && this->input_buf[0]==0xAA 
                && this->input_buf[1]==0xFF 
                && this->input_buf[2]==0x03 
                && this->input_buf[3]==0x00 
                && this->input_buf[28]==0x55 
                && this->input_buf[29]==0xCC) {
            parse_frame(this->input_buf);
            this->input_pos = 0;
        }
    }
}

void HKLD2450::parse_frame(const uint8_t *b) {
    bool need_event = false;
    for(int t = 0; t < 3; ++t) {
        int base = 4 + t * 8;
        auto raw16 = [&](int off) { 
            return uint16_t(b[base + off]) | (uint16_t(b[base + off + 1]) << 8);
        };
        auto to_s = [&](uint16_t v) {
            return (v & 0x8000)? int16_t(v & 0x7FFF): -int16_t(v & 0x7FFF);
        };
        int16_t x_mm = to_s(raw16(0));
        if (this->invert_x_) x_mm = - x_mm;
        int16_t y_mm = to_s(raw16(2));
        int8_t old_zone = this->zone_[t];
        int8_t zone = -1; // Out of zone
        if ((x_mm != 0) || (y_mm != 0)) {
            ESP_LOGD(TAG, "parse_frame: detected: [%d], (%d x %d)", t, x_mm, y_mm);
            if (this->a__ != 0) {
                float a_rad = this->a__ * M_PI / 180.f;
                float cos_a = std::cos(a_rad);
                float sin_a = std::sin(a_rad);
                float x_mm_ = float(x_mm) * cos_a - float(y_mm) * sin_a;
                float y_mm_ = float(x_mm) * sin_a + float(y_mm) * cos_a;
                x_mm = int16_t(x_mm_);
                y_mm = int16_t(y_mm_);
                ESP_LOGD(TAG, "parse_frame: rotated: [%d], (%d x %d x %d) ", t, x_mm, y_mm, this->a__);
            }
            x_mm = x_mm + this->x__;
            y_mm = y_mm + this->y__;
            ESP_LOGD(TAG, "parse_frame: moved: [%d], (%d x %d)", t, x_mm, y_mm);
            if ((x_mm >= 0) && (y_mm >= 0) && (x_mm <= this->w__) && (y_mm <= this->h__)) {
                zone = 0; // Inside room at least
                for (auto z : this->zones_) {
                    if ((x_mm >= z.x) && (y_mm >= z.y) && (x_mm <= z.x + z.w) && (y_mm <= z.y + z.h)) {
                        zone = z.id;
                    }
                }
            }
            ESP_LOGD(TAG, "parse_frame: in zone: [%d], (%d x %d) -> %d", t, x_mm, y_mm, zone);
        }
        if (zone != -1) {
            int16_t speed = to_s(raw16(4)) * 10;
            uint16_t res = raw16(0);
            this->x_[t] = x_mm;
            this->y_[t] = y_mm;
            this->sp_[t] = speed;
            this->res_[t] = res;
        }
        this->zone_[t] = zone;
        if (zone != old_zone) need_event = true;
    }
    if (need_event) this->send_event_data();
}

void HKLD2450::handle_ack_data(const uint8_t *buffer, int len) {
    // if (len < 10) return;
    // if (buffer[0]!=0xFD || buffer[1]!=0xFC || buffer[2]!=0xFB || buffer[3]!=0xFA) return;
    // if (buffer[7]!=0x01) return;
    // if (twoByteToUint(buffer[8],buffer[9])!=0x00) return;
    
    // uint8_t cmd = buffer[6];
    // // TODO
}

void HKLD2450::send_command(const uint8_t *command, size_t length) {
    static const uint8_t enable_cmd[] = { 0xFD,0xFC,0xFB,0xFA,0x04,0x00,0xFF,0x00,0x01,0x00,0x04,0x03,0x02,0x01 };
    write_array(enable_cmd, sizeof(enable_cmd));
    
    static const uint8_t header[] = { 0xFD,0xFC,0xFB,0xFA };
    uint8_t full_cmd[sizeof(header) + length];
    memcpy(full_cmd, header, sizeof(header));
    memcpy(full_cmd + sizeof(header), command, length);
    
    write_array(full_cmd, sizeof(header) + length);
    
    static const uint8_t disable_cmd[] = { 0xFD,0xFC,0xFB,0xFA,0x02,0x00,0xFE,0x00,0x04,0x03,0x02,0x01 };
    write_array(disable_cmd, sizeof(disable_cmd));
}

void HKLD2450::service_set_layout(int x, int y, int w, int h, int a) {
    this->x__ = uint16_t(x);
    this->y__ = uint16_t(y);
    this->w__ = uint16_t(w);
    this->h__ = uint16_t(h);
    this->a__ = uint16_t(a);
    this->zones_.clear();
    for (int i = 0; i < 3; i++) {
        this->zone_[i] = -1;
    }
}

void HKLD2450::service_add_zone(int x, int y, int w, int h, int f, int id) {
    Zone zone = {
        .id = uint8_t(id),
        .x = uint16_t(x),
        .y = uint16_t(y),
        .w = uint16_t(w),
        .h = uint16_t(h),
        .f = uint8_t(f),
    };
    this->zones_.push_back(zone);
}

#define ADD_EVENT_FIELD(resp, name, key_value, value_str) esphome::api::HomeassistantServiceMap name; name.set_key(esphome::StringRef(key_value)); name.value = value_str; resp.data.push_back(name);

static const std::string z_labels[3] = {"z_0", "z_1", "z_2"};
static const std::string x_labels[3] = {"x_0", "x_1", "x_2"};
static const std::string y_labels[3] = {"y_0", "y_1", "y_2"};
static const std::string sp_labels[3] = {"sp_0", "sp_1", "sp_2"};
static const std::string rs_labels[3] = {"rs_0", "rs_1", "rs_2"};

void HKLD2450::send_event_data() {
    esphome::api::HomeassistantServiceResponse resp;
    esphome::api::HomeassistantServiceMap targets_;
    targets_.set_key(esphome::StringRef("t"));
    targets_.value = std::to_string(3);
    resp.data.push_back(targets_);

    for (int i = 0; i < 3; i++) {
        ADD_EVENT_FIELD(resp, z__, z_labels[i], std::to_string(this->zone_[i]));
        if (this->zone_[i] != -1) {
            ADD_EVENT_FIELD(resp, x__, x_labels[i], std::to_string(this->x_[i]));
            ADD_EVENT_FIELD(resp, y__,  y_labels[i], std::to_string(this->y_[i]));
            ADD_EVENT_FIELD(resp, sp__, sp_labels[i], std::to_string(this->sp_[i]));
            ADD_EVENT_FIELD(resp, res__, rs_labels[i], std::to_string(this->res_[i]));
        }
    }

    resp.set_service(esphome::StringRef("esphome.hkld2450_data"));
    resp.is_event = true;
    this->api_server_->send_homeassistant_service_call(resp);

}

}
}