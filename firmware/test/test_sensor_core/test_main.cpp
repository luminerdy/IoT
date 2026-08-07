#include <cmath>

#include <unity.h>

#include "sensor_core.h"

using sensor_core::PublishPolicy;
using sensor_core::ReadingResult;
using sensor_core::SensorFilter;
using sensor_core::median_of;

void test_median_handles_odd_even_and_invalid_counts()
{
  const float odd[] = {5.0F, 1.0F, 3.0F};
  const float even[] = {4.0F, 1.0F, 3.0F, 2.0F};
  const float too_many[] = {1.0F, 2.0F, 3.0F, 4.0F, 5.0F, 6.0F};

  TEST_ASSERT_FLOAT_WITHIN(0.001F, 3.0F, median_of(odd, 3));
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 2.5F, median_of(even, 4));
  TEST_ASSERT_TRUE(std::isnan(median_of(odd, 0)));
  TEST_ASSERT_TRUE(std::isnan(median_of(too_many, 6)));
}

void test_filter_enforces_plausibility_bounds()
{
  SensorFilter filter;

  TEST_ASSERT_EQUAL(
    static_cast<int>(ReadingResult::accepted),
    static_cast<int>(filter.accept(-40.0F, 0.0F).result)
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ReadingResult::accepted),
    static_cast<int>(filter.accept(140.0F, 100.0F).result)
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ReadingResult::implausible),
    static_cast<int>(filter.accept(-40.1F, 50.0F).result)
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ReadingResult::implausible),
    static_cast<int>(filter.accept(70.0F, 100.1F).result)
  );
}

void test_filter_requires_three_consistent_outliers()
{
  SensorFilter filter;
  filter.accept(70.0F, 40.0F);
  filter.accept(71.0F, 41.0F);
  filter.accept(69.0F, 39.0F);

  auto first = filter.accept(90.0F, 42.0F);
  auto changed_candidate = filter.accept(94.0F, 42.0F);
  auto second = filter.accept(93.0F, 42.0F);
  auto third = filter.accept(92.5F, 42.0F);

  TEST_ASSERT_EQUAL(
    static_cast<int>(ReadingResult::pending_outlier), static_cast<int>(first.result)
  );
  TEST_ASSERT_EQUAL_UINT8(1, first.candidate_samples);
  TEST_ASSERT_EQUAL_UINT8(1, changed_candidate.candidate_samples);
  TEST_ASSERT_EQUAL_UINT8(2, second.candidate_samples);
  TEST_ASSERT_EQUAL(static_cast<int>(ReadingResult::accepted), static_cast<int>(third.result));
}

void test_filter_reports_window_medians_and_resets()
{
  SensorFilter filter;
  float temperature = 0.0F;
  float humidity = 0.0F;

  TEST_ASSERT_FALSE(filter.filtered_reading(&temperature, &humidity));
  for (int value = 1; value <= 6; value++) {
    filter.accept(static_cast<float>(value), static_cast<float>(value + 20));
  }
  TEST_ASSERT_TRUE(filter.filtered_reading(&temperature, &humidity));
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 4.0F, temperature);
  TEST_ASSERT_FLOAT_WITHIN(0.001F, 24.0F, humidity);

  filter.reset();
  TEST_ASSERT_FALSE(filter.filtered_reading(&temperature, &humidity));
}

void test_publish_policy_handles_initial_interval_and_confirmed_change()
{
  PublishPolicy policy;

  TEST_ASSERT_TRUE(policy.should_publish(70.0F, NAN, 0, 0, 600000, 1.0F));
  TEST_ASSERT_TRUE(policy.should_publish(70.0F, 70.0F, 600000, 0, 600000, 1.0F));
  TEST_ASSERT_FALSE(policy.should_publish(71.0F, 70.0F, 1, 0, 600000, 1.0F));
  TEST_ASSERT_FALSE(policy.should_publish(71.0F, 70.0F, 2, 0, 600000, 1.0F));
  TEST_ASSERT_TRUE(policy.should_publish(71.0F, 70.0F, 3, 0, 600000, 1.0F));
}

void test_publish_policy_resets_confirmation_after_small_change()
{
  PublishPolicy policy;

  TEST_ASSERT_FALSE(policy.should_publish(72.0F, 70.0F, 1, 0, 600000, 1.0F));
  TEST_ASSERT_FALSE(policy.should_publish(70.5F, 70.0F, 2, 0, 600000, 1.0F));
  TEST_ASSERT_FALSE(policy.should_publish(72.0F, 70.0F, 3, 0, 600000, 1.0F));
  TEST_ASSERT_FALSE(policy.should_publish(72.0F, 70.0F, 4, 0, 600000, 1.0F));
  TEST_ASSERT_TRUE(policy.should_publish(72.0F, 70.0F, 5, 0, 600000, 1.0F));
}

int main(int, char **)
{
  UNITY_BEGIN();
  RUN_TEST(test_median_handles_odd_even_and_invalid_counts);
  RUN_TEST(test_filter_enforces_plausibility_bounds);
  RUN_TEST(test_filter_requires_three_consistent_outliers);
  RUN_TEST(test_filter_reports_window_medians_and_resets);
  RUN_TEST(test_publish_policy_handles_initial_interval_and_confirmed_change);
  RUN_TEST(test_publish_policy_resets_confirmation_after_small_change);
  return UNITY_END();
}
