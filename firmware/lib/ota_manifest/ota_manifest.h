#pragma once

#include <cstddef>
#include <cstdint>

namespace ota_manifest {

constexpr std::size_t URL_CAPACITY = 192;
constexpr std::size_t SHA256_CAPACITY = 65;
constexpr std::size_t SIGNATURE_CAPACITY = 161;
constexpr std::size_t VERSION_CAPACITY = 32;
constexpr std::size_t ROLLOUT_ID_CAPACITY = 64;

struct Manifest {
  char url[URL_CAPACITY];
  char sha256[SHA256_CAPACITY];
  char signature[SIGNATURE_CAPACITY];
  char metadata_signature[SIGNATURE_CAPACITY];
  char version[VERSION_CAPACITY];
  char rollout_id[ROLLOUT_ID_CAPACITY];
  std::uint32_t size;
  std::uint32_t build_number;
};

enum class ParseResult {
  ok,
  invalid_json,
  root_not_object,
  missing_command,
  invalid_command,
  unsupported_command,
  invalid_url,
  invalid_sha256,
  invalid_signature,
  invalid_metadata_signature,
  invalid_version,
  invalid_rollout_id,
  invalid_size,
  invalid_build_number,
};

ParseResult parse(const char *payload, std::size_t length, Manifest *manifest);
const char *parse_message(ParseResult result);

bool decode_hex(const char *hex, std::uint8_t *output, std::size_t output_length);
bool sha256_matches(const char *expected_sha256, const std::uint8_t digest[32]);

using MetadataSignatureValidator = bool (*)(const Manifest &manifest, void *context);

enum class PreflightResult {
  ready,
  build_number_not_configured,
  invalid_size,
  rollback_rejected,
  metadata_signature_invalid,
};

PreflightResult validate_preflight(
  const Manifest &manifest,
  std::uint32_t configured_build_number,
  std::uint32_t stored_build_number,
  MetadataSignatureValidator signature_validator,
  void *context
);
const char *preflight_message(PreflightResult result);

using FirmwareSignatureValidator = bool (*)(
  const char *signature_hex,
  const std::uint8_t digest[32],
  void *context
);

enum class DownloadResult {
  valid,
  length_mismatch,
  sha256_mismatch,
  signature_invalid,
};

DownloadResult validate_download(
  const Manifest &manifest,
  std::size_t written,
  const std::uint8_t digest[32],
  FirmwareSignatureValidator signature_validator,
  void *context
);
const char *download_message(DownloadResult result);

}  // namespace ota_manifest
