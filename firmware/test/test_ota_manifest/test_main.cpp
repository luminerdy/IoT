#include <cstdint>
#include <cstring>
#include <string>

#include <unity.h>

#include "ota_manifest.h"

using ota_manifest::DownloadResult;
using ota_manifest::Manifest;
using ota_manifest::ParseResult;
using ota_manifest::PreflightResult;

namespace {

constexpr const char *VALID_SHA256 =
  "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";

std::string valid_manifest()
{
  return std::string("{") +
    "\"command\":\"ota_update\"," +
    "\"rolloutId\":\"rollout-test\"," +
    "\"version\":\"0.1.8-arduinojson\"," +
    "\"url\":\"http://hub.test/firmware.bin?key=test\"," +
    "\"sha256\":\"" + VALID_SHA256 + "\"," +
    "\"signature\":\"3006020101020101\"," +
    "\"size\":123," +
    "\"buildNumber\":7," +
    "\"metadataSignature\":\"3006020102020102\"}";
}

std::string replace_once(std::string value, const std::string &before, const std::string &after)
{
  const std::size_t position = value.find(before);
  TEST_ASSERT_NOT_EQUAL(std::string::npos, position);
  value.replace(position, before.size(), after);
  return value;
}

ParseResult parse_text(const std::string &payload, Manifest *manifest)
{
  return ota_manifest::parse(payload.data(), payload.size(), manifest);
}

Manifest parsed_manifest()
{
  Manifest manifest = {};
  const std::string payload = valid_manifest();
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::ok),
    static_cast<int>(parse_text(payload, &manifest))
  );
  return manifest;
}

struct ValidatorState {
  int calls;
  bool result;
};

bool metadata_validator(const Manifest &, void *context)
{
  ValidatorState *state = static_cast<ValidatorState *>(context);
  state->calls++;
  return state->result;
}

bool firmware_signature_validator(const char *, const std::uint8_t[32], void *context)
{
  ValidatorState *state = static_cast<ValidatorState *>(context);
  state->calls++;
  return state->result;
}

void expected_digest(std::uint8_t digest[32])
{
  for (std::size_t index = 0; index < 32; index++) {
    digest[index] = static_cast<std::uint8_t>(index);
  }
}

}  // namespace

void test_parser_accepts_typed_manifest_and_decodes_json_escapes()
{
  Manifest manifest = {};
  std::string payload = replace_once(
    valid_manifest(),
    "http://hub.test/firmware.bin?key=test",
    "http://hub.test/firmware.bin\\u003fkey=test"
  );

  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::ok),
    static_cast<int>(parse_text(payload, &manifest))
  );
  TEST_ASSERT_EQUAL_STRING("http://hub.test/firmware.bin?key=test", manifest.url);
  TEST_ASSERT_EQUAL_STRING(VALID_SHA256, manifest.sha256);
  TEST_ASSERT_EQUAL_STRING("0.1.8-arduinojson", manifest.version);
  TEST_ASSERT_EQUAL_STRING("rollout-test", manifest.rollout_id);
  TEST_ASSERT_EQUAL_UINT32(123, manifest.size);
  TEST_ASSERT_EQUAL_UINT32(7, manifest.build_number);
}

void test_parser_rejects_invalid_json_root_and_key_confusion()
{
  Manifest manifest = {};
  const std::string nested_command =
    "{\"note\":\"\\\"command\\\":\\\"ota_update\\\"\",\"nested\":{\"command\":\"ota_update\"}}";

  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_json),
    static_cast<int>(ota_manifest::parse("{", 1, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::root_not_object),
    static_cast<int>(ota_manifest::parse("[]", 2, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::missing_command),
    static_cast<int>(parse_text(nested_command, &manifest))
  );
}

void test_parser_rejects_invalid_or_unsupported_command()
{
  Manifest manifest = {};
  std::string invalid = replace_once(valid_manifest(), "\"ota_update\"", "7");
  std::string unsupported = replace_once(valid_manifest(), "ota_update", "restart");

  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_command),
    static_cast<int>(parse_text(invalid, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::unsupported_command),
    static_cast<int>(parse_text(unsupported, &manifest))
  );
}

void test_parser_rejects_invalid_string_and_hex_fields()
{
  Manifest manifest = {};
  const std::string empty_url = replace_once(
    valid_manifest(),
    "http://hub.test/firmware.bin?key=test",
    ""
  );
  const std::string uppercase_sha = replace_once(valid_manifest(), VALID_SHA256, std::string(64, 'A'));
  const std::string odd_signature = replace_once(
    valid_manifest(),
    "3006020101020101",
    "abc"
  );
  const std::string invalid_metadata = replace_once(
    valid_manifest(),
    "3006020102020102",
    "zz"
  );
  const std::string empty_version = replace_once(valid_manifest(), "0.1.8-arduinojson", "");
  const std::string empty_rollout = replace_once(valid_manifest(), "rollout-test", "");

  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_url),
    static_cast<int>(parse_text(empty_url, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_sha256),
    static_cast<int>(parse_text(uppercase_sha, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_signature),
    static_cast<int>(parse_text(odd_signature, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_metadata_signature),
    static_cast<int>(parse_text(invalid_metadata, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_version),
    static_cast<int>(parse_text(empty_version, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_rollout_id),
    static_cast<int>(parse_text(empty_rollout, &manifest))
  );
}

void test_parser_rejects_untyped_or_out_of_range_numbers()
{
  Manifest manifest = {};
  const std::string size_string = replace_once(valid_manifest(), "\"size\":123", "\"size\":\"123\"");
  const std::string size_zero = replace_once(valid_manifest(), "\"size\":123", "\"size\":0");
  const std::string size_fraction = replace_once(valid_manifest(), "\"size\":123", "\"size\":1.5");
  const std::string size_too_large = replace_once(
    valid_manifest(),
    "\"size\":123",
    "\"size\":2147483648"
  );
  const std::string build_string = replace_once(
    valid_manifest(),
    "\"buildNumber\":7",
    "\"buildNumber\":\"7\""
  );
  const std::string build_zero = replace_once(valid_manifest(), "\"buildNumber\":7", "\"buildNumber\":0");
  const std::string build_too_large = replace_once(
    valid_manifest(),
    "\"buildNumber\":7",
    "\"buildNumber\":4294967296"
  );

  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_size),
    static_cast<int>(parse_text(size_string, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_size),
    static_cast<int>(parse_text(size_zero, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_size),
    static_cast<int>(parse_text(size_fraction, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_size),
    static_cast<int>(parse_text(size_too_large, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_build_number),
    static_cast<int>(parse_text(build_string, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_build_number),
    static_cast<int>(parse_text(build_zero, &manifest))
  );
  TEST_ASSERT_EQUAL(
    static_cast<int>(ParseResult::invalid_build_number),
    static_cast<int>(parse_text(build_too_large, &manifest))
  );
}

void test_decode_hex_and_sha256_comparison()
{
  std::uint8_t decoded[4] = {};
  const std::uint8_t expected[] = {0x00, 0x1a, 0xB2, 0xff};
  std::uint8_t digest[32];
  expected_digest(digest);

  TEST_ASSERT_TRUE(ota_manifest::decode_hex("001aB2ff", decoded, sizeof(decoded)));
  TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, decoded, sizeof(decoded));
  TEST_ASSERT_FALSE(ota_manifest::decode_hex("001aB2f", decoded, sizeof(decoded)));
  TEST_ASSERT_FALSE(ota_manifest::decode_hex("001aB2fg", decoded, sizeof(decoded)));
  TEST_ASSERT_TRUE(ota_manifest::sha256_matches(VALID_SHA256, digest));
  digest[31] ^= 1;
  TEST_ASSERT_FALSE(ota_manifest::sha256_matches(VALID_SHA256, digest));
}

void test_preflight_gate_order_stops_before_signature_when_earlier_gate_fails()
{
  Manifest manifest = parsed_manifest();
  ValidatorState validator = {0, true};

  TEST_ASSERT_EQUAL(
    static_cast<int>(PreflightResult::build_number_not_configured),
    static_cast<int>(
      ota_manifest::validate_preflight(manifest, 0, 0, metadata_validator, &validator)
    )
  );
  TEST_ASSERT_EQUAL_INT(0, validator.calls);

  manifest.size = 0;
  TEST_ASSERT_EQUAL(
    static_cast<int>(PreflightResult::invalid_size),
    static_cast<int>(
      ota_manifest::validate_preflight(manifest, 5, 0, metadata_validator, &validator)
    )
  );
  TEST_ASSERT_EQUAL_INT(0, validator.calls);

  manifest.size = 123;
  manifest.build_number = 6;
  TEST_ASSERT_EQUAL(
    static_cast<int>(PreflightResult::rollback_rejected),
    static_cast<int>(
      ota_manifest::validate_preflight(manifest, 5, 6, metadata_validator, &validator)
    )
  );
  TEST_ASSERT_EQUAL_INT(0, validator.calls);
}

void test_preflight_validates_metadata_signature_after_build_number()
{
  Manifest manifest = parsed_manifest();
  ValidatorState validator = {0, false};

  TEST_ASSERT_EQUAL(
    static_cast<int>(PreflightResult::metadata_signature_invalid),
    static_cast<int>(
      ota_manifest::validate_preflight(manifest, 5, 6, metadata_validator, &validator)
    )
  );
  TEST_ASSERT_EQUAL_INT(1, validator.calls);

  validator.result = true;
  TEST_ASSERT_EQUAL(
    static_cast<int>(PreflightResult::ready),
    static_cast<int>(
      ota_manifest::validate_preflight(manifest, 5, 6, metadata_validator, &validator)
    )
  );
  TEST_ASSERT_EQUAL_INT(2, validator.calls);
}

void test_download_gate_order_is_length_then_sha_then_signature()
{
  Manifest manifest = parsed_manifest();
  std::uint8_t digest[32];
  expected_digest(digest);
  ValidatorState validator = {0, true};

  TEST_ASSERT_EQUAL(
    static_cast<int>(DownloadResult::length_mismatch),
    static_cast<int>(ota_manifest::validate_download(
      manifest,
      manifest.size - 1,
      digest,
      firmware_signature_validator,
      &validator
    ))
  );
  TEST_ASSERT_EQUAL_INT(0, validator.calls);

  digest[0] ^= 1;
  TEST_ASSERT_EQUAL(
    static_cast<int>(DownloadResult::sha256_mismatch),
    static_cast<int>(ota_manifest::validate_download(
      manifest,
      manifest.size,
      digest,
      firmware_signature_validator,
      &validator
    ))
  );
  TEST_ASSERT_EQUAL_INT(0, validator.calls);

  expected_digest(digest);
  validator.result = false;
  TEST_ASSERT_EQUAL(
    static_cast<int>(DownloadResult::signature_invalid),
    static_cast<int>(ota_manifest::validate_download(
      manifest,
      manifest.size,
      digest,
      firmware_signature_validator,
      &validator
    ))
  );
  TEST_ASSERT_EQUAL_INT(1, validator.calls);

  validator.result = true;
  TEST_ASSERT_EQUAL(
    static_cast<int>(DownloadResult::valid),
    static_cast<int>(ota_manifest::validate_download(
      manifest,
      manifest.size,
      digest,
      firmware_signature_validator,
      &validator
    ))
  );
  TEST_ASSERT_EQUAL_INT(2, validator.calls);
}

int main(int, char **)
{
  UNITY_BEGIN();
  RUN_TEST(test_parser_accepts_typed_manifest_and_decodes_json_escapes);
  RUN_TEST(test_parser_rejects_invalid_json_root_and_key_confusion);
  RUN_TEST(test_parser_rejects_invalid_or_unsupported_command);
  RUN_TEST(test_parser_rejects_invalid_string_and_hex_fields);
  RUN_TEST(test_parser_rejects_untyped_or_out_of_range_numbers);
  RUN_TEST(test_decode_hex_and_sha256_comparison);
  RUN_TEST(test_preflight_gate_order_stops_before_signature_when_earlier_gate_fails);
  RUN_TEST(test_preflight_validates_metadata_signature_after_build_number);
  RUN_TEST(test_download_gate_order_is_length_then_sha_then_signature);
  return UNITY_END();
}
