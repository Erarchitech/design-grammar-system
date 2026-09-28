using System.Net;
using System.Net.Http;
using DG.Core.Data;
using DG.Core.Models;

namespace DG.Tests;

public sealed class DataServiceRequestAuthTests
{
    // --- TryApplyConnectorToken ---

    [Fact]
    public void TryApplyConnectorToken_WellFormedTokenWithWhitespace_TrimsAndSetsBearerHeader()
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "http://localhost:8000/validation/publish");

        var applied = DataServiceRequestAuth.TryApplyConnectorToken(request, "  dgc_abc  ", out var failure);

        Assert.True(applied);
        Assert.Equal(PublishAuthOutcome.Ok, failure);
        Assert.NotNull(request.Headers.Authorization);
        Assert.Equal("Bearer", request.Headers.Authorization!.Scheme);
        Assert.Equal("dgc_abc", request.Headers.Authorization.Parameter);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void TryApplyConnectorToken_NullOrBlankToken_ReturnsFalseWithMissingTokenAndNoHeader(string? token)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "http://localhost:8000/validation/publish");

        var applied = DataServiceRequestAuth.TryApplyConnectorToken(request, token, out var failure);

        Assert.False(applied);
        Assert.Equal(PublishAuthOutcome.MissingToken, failure);
        Assert.Null(request.Headers.Authorization);
    }

    [Fact]
    public void TryApplyConnectorToken_WrongPrefix_ReturnsFalseWithMalformedTokenAndNoHeader()
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "http://localhost:8000/validation/publish");

        var applied = DataServiceRequestAuth.TryApplyConnectorToken(request, "abc", out var failure);

        Assert.False(applied);
        Assert.Equal(PublishAuthOutcome.MalformedToken, failure);
        Assert.Null(request.Headers.Authorization);
    }

    // --- ClassifyStatus ---

    [Theory]
    [InlineData(HttpStatusCode.OK, PublishAuthOutcome.Ok)]
    [InlineData(HttpStatusCode.Created, PublishAuthOutcome.Ok)]
    [InlineData(HttpStatusCode.Unauthorized, PublishAuthOutcome.Rejected)]
    [InlineData(HttpStatusCode.Forbidden, PublishAuthOutcome.Forbidden)]
    [InlineData(HttpStatusCode.NotFound, PublishAuthOutcome.Failed)]
    [InlineData(HttpStatusCode.InternalServerError, PublishAuthOutcome.Failed)]
    [InlineData(HttpStatusCode.BadGateway, PublishAuthOutcome.Failed)]
    public void ClassifyStatus_MapsStatusCodeToExpectedOutcome(HttpStatusCode code, PublishAuthOutcome expected)
    {
        var result = DataServiceRequestAuth.ClassifyStatus(code);

        Assert.Equal(expected, result);
    }

    // --- ConnectionInfo credential-free default (D-04 Correction) ---

    [Fact]
    public void ConnectionInfo_DefaultPassword_IsEmpty()
    {
        var info = new ConnectionInfo();

        Assert.Equal(string.Empty, info.Password);
    }
}
