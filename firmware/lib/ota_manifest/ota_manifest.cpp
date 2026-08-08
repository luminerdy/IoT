#include "ota_manifest.h"

#include <ArduinoJson.h>

#include <cstring>

namespace ota_manifest {
namespace {

constexpr std::uint32_t MAX_FIRMWARE_SIZE = 0x7FFFFFFFU;

int hex_nibble(char value)
{
  if (value >= '0' && value <= '9') {
    return value - '0';
  }
  if (value >= 'a' && value <= 'f') {
    return value - 'a' + 10;
  }
  if (value >= 'A' && value <= 'F') {
    return value - 'A' + 10;
  }
  return -1;
}

bool is_lower_hex(const char *value, std::size_t expected_length = 0)
{
  if (value == nullptr) {
    return false;
  }
  const std::size_t length = std::strlen(value);
  if (length == 0 || (expected_length != 0 && length != expected_length)) {
    return false;
  }
  for (std::size_t index = 0; index < length; index++) {
    const char current = value[index];
    if (!((current >= '0' && current <= '9') || (current >= 'a' && current <= 'f'))) {
      return false;
    }
  }
  return true;
}

bool copy_required_string(
  JsonObjectConst root,
  const char *key,
  char *destination,
  std::size_t capacity
)
{
  JsonVariantConst value = root[key];
  if (!value.is<const char *>()) {
    return false;
  }
  const char *text = value.as<const char *>();
  if (text == nullptr) {
    return false;
  }
  const std::size_t length = std::strlen(text);
  if (length == 0 || length >= capacity) {
    return false;
  }
  std::memcpy(destination, text, length + 1);
  return true;
}

}  // namespace

ParseResult parse(const char *payload, std::size_t length, Manifest *manifest)
{
  if (payload == nullptr || manifest == nullptr || length == 0) {
    return ParseResult::invalid_json;
  }

  JsonDocument document;
  const DeserializationError error = deserializeJson(document, payload, length);
  if (error) {
    return ParseResult::invalid_json;
  }
  if (!document.is<JsonObject>()) {
    return ParseResult::root_not_object;
  }

  JsonObjectConst root = document.as<JsonObjectConst>();
  JsonVariantConst command_value = root["command"];
  if (command_value.isNull()) {
    return ParseResult::missing_command;
  }
  if (!command_value.is<const char *>()) {
    return ParseResult::invalid_command;
  }
  const char *command = command_value.as<const char *>();
  if (command == nullptr || std::strcmp(command, "ota_update") != 0) {
    return ParseResult::unsupported_command;
  }

  Manifest parsed = {};
  if (!copy_required_string(root, "url", parsed.url, sizeof(parsed.url))) {
    return ParseResult::invalid_url;
  }
  if (!copy_required_string(root, "sha256", parsed.sha256, sizeof(parsed.sha256)) ||
      !is_lower_hex(parsed.sha256, 64)) {
    return ParseResult::invalid_sha256;
  }
  if (!copy_required_string(root, "signature", parsed.signature, sizeof(parsed.signature)) ||
      std::strlen(parsed.signature) % 2 != 0 || !is_lower_hex(parsed.signature)) {
    return ParseResult::invalid_signature;
  }
  if (!copy_required_string(
        root,
        "metadataSignature",
        parsed.metadata_signature,
        sizeof(parsed.metadata_signature)
      ) ||
      std::strlen(parsed.metadata_signature) % 2 != 0 ||
      !is_lower_hex(parsed.metadata_signature)) {
    return ParseResult::invalid_metadata_signature;
  }
  if (!copy_required_string(root, "version", parsed.version, sizeof(parsed.version))) {
    return ParseResult::invalid_version;
  }
  if (!copy_required_string(root, "rolloutId", parsed.rollout_id, sizeof(parsed.rollout_id))) {
    return ParseResult::invalid_rollout_id;
  }

  JsonVariantConst size_value = root["size"];
  if (!size_value.is<std::uint32_t>()) {
    return ParseResult::invalid_size;
  }
  parsed.size = size_value.as<std::uint32_t>();
  if (parsed.size == 0 || parsed.size > MAX_FIRMWARE_SIZE) {
    return ParseResult::invalid_size;
  }

  JsonVariantConst build_number_value = root["buildNumber"];
  if (!build_number_value.is<std::uint32_t>()) {
    return ParseResult::invalid_build_number;
  }
  parsed.build_number = build_number_value.as<std::uint32_t>();
  if (parsed.build_number == 0) {
    return ParseResult::invalid_build_number;
  }

  *manifest = parsed;
  return ParseResult::ok;
}

const char *parse_message(ParseResult result)
{
  switch (result) {
    case ParseResult::ok:
      return "ota command parsed";
    case ParseResult::invalid_json:
      return "invalid json";
    case ParseResult::root_not_object:
      return "invalid ota document";
    case ParseResult::missing_command:
      return "missing command";
    case ParseResult::invalid_command:
      return "invalid command";
    case ParseResult::unsupported_command:
      return "unsupported command";
    case ParseResult::invalid_url:
      return "invalid ota url";
    case ParseResult::invalid_sha256:
      return "invalid ota sha256";
    case ParseResult::invalid_signature:
      return "invalid ota signature";
    case ParseResult::invalid_metadata_signature:
      return "invalid ota metadata signature";
    case ParseResult::invalid_version:
      return "invalid ota version";
    case ParseResult::invalid_rollout_id:
      return "invalid ota rollout id";
    case ParseResult::invalid_size:
      return "invalid ota size";
    case ParseResult::invalid_build_number:
      return "invalid ota build number";
  }
  return "invalid ota command";
}

bool decode_hex(const char *hex, std::uint8_t *output, std::size_t output_length)
{
  if (hex == nullptr || output == nullptr || std::strlen(hex) != output_length * 2) {
    return false;
  }

  for (std::size_t index = 0; index < output_length; index++) {
    const int high = hex_nibble(hex[index * 2]);
    const int low = hex_nibble(hex[(index * 2) + 1]);
    if (high < 0 || low < 0) {
      return false;
    }
    output[index] = static_cast<std::uint8_t>((high << 4) | low);
  }
  return true;
}

bool sha256_matches(const char *expected_sha256, const std::uint8_t digest[32])
{
  std::uint8_t expected[32];
  if (!decode_hex(expected_sha256, expected, sizeof(expected))) {
    return false;
  }
  std::uint8_t difference = 0;
  for (std::size_t index = 0; index < sizeof(expected); index++) {
    difference |= static_cast<std::uint8_t>(expected[index] ^ digest[index]);
  }
  return difference == 0;
}

PreflightResult validate_preflight(
  const Manifest &manifest,
  std::uint32_t configured_build_number,
  std::uint32_t stored_build_number,
  MetadataSignatureValidator signature_validator,
  void *context
)
{
  if (configured_build_number == 0) {
    return PreflightResult::build_number_not_configured;
  }
  if (manifest.size == 0 || manifest.size > MAX_FIRMWARE_SIZE) {
    return PreflightResult::invalid_size;
  }
  const std::uint32_t highest_build_number =
    stored_build_number > configured_build_number ? stored_build_number : configured_build_number;
  if (manifest.build_number <= highest_build_number) {
    return PreflightResult::rollback_rejected;
  }
  if (signature_validator == nullptr || !signature_validator(manifest, context)) {
    return PreflightResult::metadata_signature_invalid;
  }
  return PreflightResult::ready;
}

const char *preflight_message(PreflightResult result)
{
  switch (result) {
    case PreflightResult::ready:
      return "ota preflight passed";
    case PreflightResult::build_number_not_configured:
      return "ota build number not configured";
    case PreflightResult::invalid_size:
      return "missing firmware size";
    case PreflightResult::rollback_rejected:
      return "firmware rollback rejected";
    case PreflightResult::metadata_signature_invalid:
      return "ota metadata signature invalid";
  }
  return "ota preflight failed";
}

DownloadResult validate_download(
  const Manifest &manifest,
  std::size_t written,
  const std::uint8_t digest[32],
  FirmwareSignatureValidator signature_validator,
  void *context
)
{
  if (written != manifest.size) {
    return DownloadResult::length_mismatch;
  }
  if (!sha256_matches(manifest.sha256, digest)) {
    return DownloadResult::sha256_mismatch;
  }
  if (signature_validator == nullptr ||
      !signature_validator(manifest.signature, digest, context)) {
    return DownloadResult::signature_invalid;
  }
  return DownloadResult::valid;
}

const char *download_message(DownloadResult result)
{
  switch (result) {
    case DownloadResult::valid:
      return "firmware verified";
    case DownloadResult::length_mismatch:
      return "firmware length mismatch";
    case DownloadResult::sha256_mismatch:
      return "firmware sha256 mismatch";
    case DownloadResult::signature_invalid:
      return "firmware signature invalid";
  }
  return "firmware verification failed";
}

}  // namespace ota_manifest
