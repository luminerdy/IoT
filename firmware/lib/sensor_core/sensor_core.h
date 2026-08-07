#pragma once

#include <cstddef>
#include <cstdint>

namespace sensor_core {

constexpr std::size_t FILTER_WINDOW_SIZE = 5;
constexpr std::uint8_t CHANGE_CONFIRMATION_SAMPLES = 3;
constexpr float MIN_VALID_TEMPERATURE_F = -40.0F;
constexpr float MAX_VALID_TEMPERATURE_F = 140.0F;
constexpr float MIN_VALID_HUMIDITY = 0.0F;
constexpr float MAX_VALID_HUMIDITY = 100.0F;
constexpr float OUTLIER_TEMPERATURE_DELTA_F = 8.0F;
constexpr float OUTLIER_CONFIRMATION_DELTA_F = 2.0F;
constexpr std::uint8_t OUTLIER_CONFIRMATION_SAMPLES = 3;

float median_of(const float *values, std::size_t count);

enum class ReadingResult {
  accepted,
  implausible,
  pending_outlier,
};

struct ReadingDecision {
  ReadingResult result;
  float baseline_temperature_f;
  std::uint8_t candidate_samples;
};

class SensorFilter {
 public:
  SensorFilter();

  void reset();
  ReadingDecision accept(float temperature_f, float humidity);
  bool filtered_reading(float *temperature_f, float *humidity) const;

 private:
  float temperature_window_[FILTER_WINDOW_SIZE];
  float humidity_window_[FILTER_WINDOW_SIZE];
  std::size_t sample_count_;
  std::size_t sample_index_;
  float candidate_outlier_temperature_f_;
  std::uint8_t candidate_outlier_samples_;
};

class PublishPolicy {
 public:
  PublishPolicy();

  void reset();
  bool should_publish(
    float temperature_f,
    float last_temperature_f,
    unsigned long now_ms,
    unsigned long last_report_ms,
    unsigned long report_interval_ms,
    float change_threshold_f
  );

 private:
  std::uint8_t consecutive_change_samples_;
};

}  // namespace sensor_core
