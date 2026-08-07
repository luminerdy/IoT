#include "sensor_core.h"

#include <cmath>

namespace sensor_core {

float median_of(const float *values, std::size_t count)
{
  if (count == 0 || count > FILTER_WINDOW_SIZE) {
    return NAN;
  }

  float sorted[FILTER_WINDOW_SIZE];
  for (std::size_t i = 0; i < count; i++) {
    sorted[i] = values[i];
  }

  for (std::size_t i = 1; i < count; i++) {
    float current = sorted[i];
    std::size_t j = i;
    while (j > 0 && sorted[j - 1] > current) {
      sorted[j] = sorted[j - 1];
      j--;
    }
    sorted[j] = current;
  }

  if (count % 2 == 1) {
    return sorted[count / 2];
  }
  return (sorted[(count / 2) - 1] + sorted[count / 2]) / 2.0F;
}

SensorFilter::SensorFilter()
{
  reset();
}

void SensorFilter::reset()
{
  sample_count_ = 0;
  sample_index_ = 0;
  candidate_outlier_temperature_f_ = NAN;
  candidate_outlier_samples_ = 0;
}

ReadingDecision SensorFilter::accept(float temperature_f, float humidity)
{
  if (
    temperature_f < MIN_VALID_TEMPERATURE_F ||
    temperature_f > MAX_VALID_TEMPERATURE_F ||
    humidity < MIN_VALID_HUMIDITY ||
    humidity > MAX_VALID_HUMIDITY
  ) {
    return {ReadingResult::implausible, NAN, 0};
  }

  float baseline_temperature_f = NAN;
  if (sample_count_ >= 3) {
    baseline_temperature_f = median_of(temperature_window_, sample_count_);
    if (std::fabs(temperature_f - baseline_temperature_f) > OUTLIER_TEMPERATURE_DELTA_F) {
      if (
        std::isnan(candidate_outlier_temperature_f_) ||
        std::fabs(temperature_f - candidate_outlier_temperature_f_) >
          OUTLIER_CONFIRMATION_DELTA_F
      ) {
        candidate_outlier_temperature_f_ = temperature_f;
        candidate_outlier_samples_ = 1;
      } else {
        candidate_outlier_samples_++;
      }

      if (candidate_outlier_samples_ < OUTLIER_CONFIRMATION_SAMPLES) {
        return {
          ReadingResult::pending_outlier,
          baseline_temperature_f,
          candidate_outlier_samples_,
        };
      }
    } else {
      candidate_outlier_temperature_f_ = NAN;
      candidate_outlier_samples_ = 0;
    }
  }

  temperature_window_[sample_index_] = temperature_f;
  humidity_window_[sample_index_] = humidity;
  sample_index_ = (sample_index_ + 1) % FILTER_WINDOW_SIZE;
  if (sample_count_ < FILTER_WINDOW_SIZE) {
    sample_count_++;
  }

  return {
    ReadingResult::accepted,
    baseline_temperature_f,
    candidate_outlier_samples_,
  };
}

bool SensorFilter::filtered_reading(float *temperature_f, float *humidity) const
{
  if (sample_count_ == 0) {
    return false;
  }

  *temperature_f = median_of(temperature_window_, sample_count_);
  *humidity = median_of(humidity_window_, sample_count_);
  return true;
}

PublishPolicy::PublishPolicy()
{
  reset();
}

void PublishPolicy::reset()
{
  consecutive_change_samples_ = 0;
}

bool PublishPolicy::should_publish(
  float temperature_f,
  float last_temperature_f,
  unsigned long now_ms,
  unsigned long last_report_ms,
  unsigned long report_interval_ms,
  float change_threshold_f
)
{
  if (std::isnan(last_temperature_f)) {
    reset();
    return true;
  }
  if (now_ms - last_report_ms >= report_interval_ms) {
    reset();
    return true;
  }

  if (std::fabs(temperature_f - last_temperature_f) >= change_threshold_f) {
    consecutive_change_samples_++;
    return consecutive_change_samples_ >= CHANGE_CONFIRMATION_SAMPLES;
  }

  reset();
  return false;
}

}  // namespace sensor_core
