using System.Security.Cryptography;

namespace DG.Core.Compat;

/// <summary>
/// Phase 1303-15: static helpers that exist on .NET 5+ as members of BCL types (and so cannot be polyfilled with
/// extension methods) but are missing on .NET Framework 4.8, which Rhino.Inside.Revit uses inside Revit 2024.
/// Behaviour matches the .NET members they replace (upper-case hex, ArgumentNullException with the argument name).
/// </summary>
public static class DgCompat
{
    public static void ThrowIfNull(object? argument, string? paramName = null)
    {
        if (argument is null)
        {
            throw new ArgumentNullException(paramName);
        }
    }

    public static byte[] Sha256(byte[] data)
    {
        using var sha = SHA256.Create();
        return sha.ComputeHash(data);
    }

    public static string ToHex(byte[] bytes) => ToHex(bytes, 0, bytes.Length);

    public static string ToHex(byte[] bytes, int offset, int length)
    {
        var chars = new char[length * 2];
        const string digits = "0123456789ABCDEF";
        for (var i = 0; i < length; i++)
        {
            var b = bytes[offset + i];
            chars[2 * i] = digits[b >> 4];
            chars[2 * i + 1] = digits[b & 0xF];
        }

        return new string(chars);
    }

    public static bool IsFinite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
}
