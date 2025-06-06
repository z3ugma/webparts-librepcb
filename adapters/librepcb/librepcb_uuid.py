# Global imports
import hashlib
import uuid


def create_derived_uuidv4(base_uuid: uuid.UUID, text_modifier: str) -> uuid.UUID:
    """
    Deterministically creates a new UUIDv4 based on an existing UUIDv4
    and a piece of text.

    The process involves:
    1. Concatenating the byte representation of the base_uuid and the UTF-8
       encoded text_modifier.
    2. Hashing this concatenated data (e.g., using SHA-256).
    3. Taking the first 16 bytes (128 bits) of the hash.
    4. Adjusting the bits to ensure it's a valid Version 4, RFC 4122 UUID.

    Args:
        base_uuid: The original uuid.UUID object (must be v4 if you want to
                   think of this as a "mutation" of a v4, though any UUID
                   can serve as the byte input).
        text_modifier: The string to combine with the base_uuid.

    Returns:
        A new, deterministically generated UUIDv4.
    """
    # 1. Get bytes from base_uuid and text_modifier
    base_uuid_bytes = base_uuid.bytes
    text_modifier_bytes = text_modifier.encode("utf-8")

    # 2. Concatenate and hash
    combined_data = base_uuid_bytes + text_modifier_bytes

    # Using SHA-256. It produces a 32-byte (256-bit) hash.
    # We'll take the first 16 bytes (128 bits) for our UUID.
    hasher = hashlib.sha256()
    hasher.update(combined_data)
    hashed_bytes = hasher.digest()

    # 3. Take the first 16 bytes
    derived_bytes = hashed_bytes[:16]

    # 4. Adjust bits for Version 4 and RFC 4122 variant
    # Convert bytes to a mutable list of integers (0-255)
    mutable_bytes = list(derived_bytes)

    # Set version to 4
    # Version is in the most significant 4 bits of the 7th byte (index 6)
    # 0100xxxx
    mutable_bytes[6] = (mutable_bytes[6] & 0x0F) | 0x40

    # Set variant to RFC 4122
    # Variant is in the most significant 2 or 3 bits of the 9th byte (index 8)
    # 10xxxxxx
    mutable_bytes[8] = (mutable_bytes[8] & 0x3F) | 0x80

    return uuid.UUID(bytes=bytes(mutable_bytes))


if __name__ == "__main__":
    # --- Example Usage ---
    # An existing UUIDv4 (replace with one you have)
    original_uuid_str = "d79d354b-62bd-4866-996a-78941c575e78"
    original_uuid = uuid.UUID(original_uuid_str)
    if original_uuid.version != 4:
        print(
            f"Warning: Original UUID '{original_uuid_str}' is not version 4. "
            "The function will still work but the output will be v4."
        )

    text1 = "project_alpha_component_x"
    text2 = "project_alpha_component_y"
    text3 = "project_alpha_component_x"  # Same as text1

    derived1 = create_derived_uuidv4(original_uuid, text1)
    derived2 = create_derived_uuidv4(original_uuid, text2)
    derived3 = create_derived_uuidv4(original_uuid, text3)  # Should be same as derived1

    print(f"Original UUID: {original_uuid} (Version {original_uuid.version})")
    print(
        f"Derived with '{text1}': {derived1} (Version {derived1.version}, Variant: {derived1.variant})"
    )
    print(
        f"Derived with '{text2}': {derived2} (Version {derived2.version}, Variant: {derived2.variant})"
    )
    print(
        f"Derived with '{text3}': {derived3} (Version {derived3.version}, Variant: {derived3.variant})"
    )

    assert derived1 == derived3
    assert derived1 != derived2
    assert derived1.version == 4
    assert derived1.variant == uuid.RFC_4122
    assert derived2.version == 4
    assert derived2.variant == uuid.RFC_4122

    # Using a different base UUID
    another_original_uuid_str = "512dc09f-9434-4046-8381-248b8b264b12"
    another_original_uuid = uuid.UUID(another_original_uuid_str)
    if another_original_uuid.version != 4:
        print(f"Warning: Original UUID '{another_original_uuid_str}' is not version 4.")

    derived_alt_base = create_derived_uuidv4(another_original_uuid, text1)
    print(
        f"\nOriginal UUID 2: {another_original_uuid} (Version {another_original_uuid.version})"
    )
    print(
        f"Derived with '{text1}' (alt base): {derived_alt_base} (Version {derived_alt_base.version})"
    )

    assert derived_alt_base != derived1
