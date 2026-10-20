#if NETFRAMEWORK
// Phase 1303-15: .NET Framework 4.8 polyfills so DG.Core and DG.gha load in Rhino.Inside.Revit for Revit 2024
// (.NET Framework runtime). Compiled only for net48; the net7.0/net9.0 builds use the BCL members.

namespace System.Threading.Tasks
{
    public static class DgTaskPolyfills
    {
        public static async Task<T> WaitAsync<T>(this Task<T> task, TimeSpan timeout, CancellationToken cancellationToken)
        {
            await WaitAsync((Task)task, timeout, cancellationToken).ConfigureAwait(false);
            return await task.ConfigureAwait(false);
        }

        public static async Task WaitAsync(this Task task, TimeSpan timeout, CancellationToken cancellationToken)
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            var delay = Task.Delay(timeout, cts.Token);
            var finished = await Task.WhenAny(task, delay).ConfigureAwait(false);
            if (finished != task)
            {
                cancellationToken.ThrowIfCancellationRequested();
                throw new TimeoutException();
            }

            cts.Cancel();
            await task.ConfigureAwait(false);
        }
    }
}

namespace System.Collections.Generic
{
    public static class DgCollectionPolyfills
    {
        public static void Deconstruct<TKey, TValue>(this KeyValuePair<TKey, TValue> pair, out TKey key, out TValue value)
        {
            key = pair.Key;
            value = pair.Value;
        }

        public static TValue? GetValueOrDefault<TKey, TValue>(this IReadOnlyDictionary<TKey, TValue> dictionary, TKey key)
            => dictionary.TryGetValue(key, out var value) ? value : default;

        public static TValue GetValueOrDefault<TKey, TValue>(this IReadOnlyDictionary<TKey, TValue> dictionary, TKey key, TValue defaultValue)
            => dictionary.TryGetValue(key, out var value) ? value : defaultValue;
    }

    public sealed class ReferenceEqualityComparer : IEqualityComparer<object?>
    {
        public static ReferenceEqualityComparer Instance { get; } = new();

        private ReferenceEqualityComparer()
        {
        }

        public new bool Equals(object? x, object? y) => ReferenceEquals(x, y);

        public int GetHashCode(object? obj) => System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(obj!);
    }
}

namespace System
{
    public static class MathF
    {
        public static float Sqrt(float x) => (float)Math.Sqrt(x);
    }

    public static class DgStringPolyfills
    {
        public static bool Contains(this string text, string value, StringComparison comparison)
            => text.IndexOf(value, comparison) >= 0;

        public static bool Contains(this string text, char value) => text.IndexOf(value) >= 0;

        public static bool Contains(this string text, char value, StringComparison comparison)
            => text.IndexOf(value.ToString(), comparison) >= 0;

        public static bool StartsWith(this string text, char value) => text.Length > 0 && text[0] == value;

        public static bool EndsWith(this string text, char value) => text.Length > 0 && text[text.Length - 1] == value;

        public static string[] Split(this string text, char separator, StringSplitOptions options)
            => text.Split(new[] { separator }, options);

        public static string[] Split(this string text, string separator, StringSplitOptions options = StringSplitOptions.None)
            => text.Split(new[] { separator }, options);

        public static string[] Split(this string text, char separator, int count, StringSplitOptions options = StringSplitOptions.None)
            => text.Split(new[] { separator }, count, options);

        public static string Replace(this string text, string oldValue, string? newValue, StringComparison comparison)
        {
            if (comparison == StringComparison.Ordinal)
            {
                return text.Replace(oldValue, newValue);
            }

            var sb = new Text.StringBuilder();
            var index = 0;
            while (true)
            {
                var found = text.IndexOf(oldValue, index, comparison);
                if (found < 0)
                {
                    break;
                }

                sb.Append(text, index, found - index).Append(newValue);
                index = found + oldValue.Length;
            }

            return sb.Append(text, index, text.Length - index).ToString();
        }
    }
}

namespace System.IO
{
    public static class DgStreamPolyfills
    {
        public static Task WriteLineAsync(this TextWriter writer, ReadOnlyMemory<char> buffer, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return writer.WriteLineAsync(buffer.ToString());
        }

        public static async Task<int> ReadAsync(this Stream stream, Memory<byte> buffer, CancellationToken cancellationToken)
        {
            if (Runtime.InteropServices.MemoryMarshal.TryGetArray<byte>(buffer, out var segment))
            {
                return await stream.ReadAsync(segment.Array!, segment.Offset, segment.Count, cancellationToken).ConfigureAwait(false);
            }

            var temp = new byte[buffer.Length];
            var read = await stream.ReadAsync(temp, 0, temp.Length, cancellationToken).ConfigureAwait(false);
            temp.AsSpan(0, read).CopyTo(buffer.Span);
            return read;
        }
    }
}

namespace System.Net.Sockets
{
    public static class DgSocketPolyfills
    {
        /// <summary>Cancellation stops the listener, which ends the pending accept (the .NET 5+ overload's effect).</summary>
        public static async Task<TcpClient> AcceptTcpClientAsync(this TcpListener listener, CancellationToken cancellationToken)
        {
            using (cancellationToken.Register(listener.Stop))
            {
                try
                {
                    return await listener.AcceptTcpClientAsync().ConfigureAwait(false);
                }
                catch (Exception) when (cancellationToken.IsCancellationRequested)
                {
                    throw new OperationCanceledException(cancellationToken);
                }
            }
        }
    }
}

namespace System.Net.Http
{
    public static class DgHttpPolyfills
    {
        public static Task<string> ReadAsStringAsync(this HttpContent content, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return content.ReadAsStringAsync();
        }
    }
}
#endif
