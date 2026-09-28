using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;

namespace DG.Core.Data;

/// <summary>
/// Applies the connector's <c>dgc_</c> platform token to outgoing data-service
/// publish requests (VALIDATOR, COMPUTGRAPH PUBLISH) and classifies the HTTP
/// response status those requests come back with (D-04, Correction 5).
///
/// The token flows only into the Authorization header — never into a field,
/// log, or exception message. This mirrors the discipline already followed by
/// <see cref="ConnectorHeartbeatClient"/>. This class has no Grasshopper SDK
/// dependency so it is directly testable from DG.Tests.
/// </summary>
public static class DataServiceRequestAuth
{
    /// <summary>The required prefix for a well-formed connector platform token.</summary>
    public const string TokenPrefix = "dgc_";

    /// <summary>
    /// Trims <paramref name="token"/> and, if it is a well-formed <c>dgc_</c>
    /// token, sets <paramref name="request"/>'s Authorization header to
    /// <c>Bearer &lt;token&gt;</c> and returns true. On failure no header is
    /// set and the specific reason is returned via <paramref name="failure"/>.
    /// </summary>
    public static bool TryApplyConnectorToken(
        HttpRequestMessage request,
        string? token,
        out PublishAuthOutcome failure)
    {
        if (request is null)
        {
            throw new ArgumentNullException(nameof(request));
        }

        var trimmed = token?.Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            failure = PublishAuthOutcome.MissingToken;
            return false;
        }

        if (!trimmed.StartsWith(TokenPrefix, StringComparison.Ordinal))
        {
            failure = PublishAuthOutcome.MalformedToken;
            return false;
        }

        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", trimmed);
        failure = PublishAuthOutcome.Ok;
        return true;
    }

    /// <summary>
    /// Maps an HTTP status code from a publish response to a
    /// <see cref="PublishAuthOutcome"/>: any 2xx is <see cref="PublishAuthOutcome.Ok"/>,
    /// 401 is <see cref="PublishAuthOutcome.Rejected"/>, 403 is
    /// <see cref="PublishAuthOutcome.Forbidden"/>, everything else is
    /// <see cref="PublishAuthOutcome.Failed"/>.
    /// </summary>
    public static PublishAuthOutcome ClassifyStatus(HttpStatusCode code)
    {
        var numeric = (int)code;
        if (numeric is >= 200 and < 300)
        {
            return PublishAuthOutcome.Ok;
        }

        return code switch
        {
            HttpStatusCode.Unauthorized => PublishAuthOutcome.Rejected,
            HttpStatusCode.Forbidden => PublishAuthOutcome.Forbidden,
            _ => PublishAuthOutcome.Failed,
        };
    }
}

/// <summary>Outcome of applying or validating a connector platform token on a publish request.</summary>
public enum PublishAuthOutcome
{
    Ok,
    MissingToken,
    MalformedToken,
    Rejected,
    Forbidden,
    Failed,
}
