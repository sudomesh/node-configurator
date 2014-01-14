
var StickerGenerator = function(elementID, w, h) {

    this.canvas = null;
    this.ctx = null;

    // w and h are with and height of final render.
    // elementID is the id of a <canvas> tag 
    // used for displaying the preview.
    // pw and ph are width and height of preview
    // if pw and ph are not specified, then the
    // current width and height of the <canvas> tag is used.
    this.init = function(w, h, elementID, pw, ph) {
        this.pCanvas = document.getElementById(elementID);
        this.pCtx = this.pCanvas.getContext('2d');
        this.w = w || 200;
        this.h = h || 200;
        this.pw = pw;
        if(!this.pw) {
            this.pw = $('#'+elementID).width();
        }
        if(!this.ph) {
            this.ph = $('#'+elementID).height();
        }
        this.ctx = this.newContext(w, h);
        this.pFactor = this.pw / this.w;
        this.pCtx.scale(this.pFactor, this.pFactor);
    };

    this.newContext = function(w, h){
	      var canvas = document.createElement('canvas');
	      canvas.width = w;
	      canvas.height = h;

        var ctx = canvas.getContext('2d');
	      ctx.shadowBlur = 0;
	      ctx.globalAlpha = 1.0;
        ctx.fillStyle = "rgba(255, 255, 255, 1.0)";
        ctx.fillRect(0, 0, this.w, this.h);
        ctx.fillStyle = "rgba(0, 0, 0, 1.0)";
        // disable smoothing (moz only);
        ctx.mozImageSmoothingEnabled = false;

	      return ctx;
    };
    
    this.draw = function(info) {
        this.drawSticker(this.ctx, info);
        this.drawSticker(this.pCtx, info);
    };

    this.drawSticker = function(ctx, info) {
        this.curLine = 0;
        this.drawLine(ctx, "This is the power");
        this.drawLine(ctx, "supply for your");
        this.drawLine(ctx, "sudomesh", true);
        this.drawLine(ctx, "node", true);
        this.drawLine(ctx, "---------------");
        this.drawLine(ctx, "To change your");
        this.drawLine(ctx, "node settings");
        this.drawLine(ctx, "connect to the");
        this.drawLine(ctx, "wifi network:");
        this.drawLine(ctx, info.private_wifi_ssid, true);
        this.drawLine(ctx, "wifi password:");
        this.drawLine(ctx, info.private_wifi_password, true);
        this.drawLine(ctx, "go to website:");
        this.drawLine(ctx, "http://my.node/", true);
        this.drawLine(ctx, "username is:");
        this.drawLine(ctx, "root", true);
        this.drawLine(ctx, "password is:");
        this.drawLine(ctx, info.root_password, true);
        this.drawLine(ctx, "for support go to");
        this.drawLine(ctx, "h.sudoroom.org", true);
    };

    this.drawLine = function(ctx, text, bold) {
        var offset = this.curLine * 41 + 50;
	      var middle = this.w / 2;
	      ctx.font = (bold ? 'bold ' : '') + '31px sans-serif' 
        ctx.textAlign = 'center';
	      ctx.fillText(text, middle, offset);
        this.curLine++;
    };

    this.toDataURL = function() {
        return this.ctx.canvas.toDataURL('image/png');
    };

    this.isBrowserSupported = function() {
	      function supportsToDataURL() {
	          var c = document.createElement("canvas");
	          var data = c.toDataURL("image/png");
	          return (data.indexOf("data:image/png") == 0);
	      }
	      
	      if(Modernizr.canvas
	         && Modernizr.canvastext
	         && Modernizr.fontface
	         && supportsToDataURL()) {
	          return true;
	      } else {
	          return false;
	      }
    };

    this.drawCircle = function(ctx) {
	      ctx.beginPath();
	      ctx.arc(40, 0, 40, 0, Math.PI*2);
	      ctx.lineWidth = 8;
	      ctx.stroke();
	      ctx.closePath();
    };

    this.drawRoundedRect = function(ctx, x, y, w, h, r) {
	      ctx.save();
	      ctx.translate(x, y);
	      ctx.moveTo(0, r);
	      ctx.arc(r, r, r, Math.PI, Math.PI*1.5);
	      ctx.lineTo(w-r, 0);
	      ctx.arc(w-r, r, r, Math.PI*1.5, Math.PI*2);
	      ctx.lineTo(w, h-r);
	      ctx.arc(w-r, h-r, r, 0, Math.PI*0.5);
	      ctx.lineTo(r, h);
	      ctx.arc(r, h-r, r, Math.PI*0.5, Math.PI);
	      ctx.lineTo(0, r);
	      ctx.restore();
    };


    this.drawPerson = function(ctx, x, y) {
	      var m = this.measure(ctx);
	      ctx.save();
	      ctx.translate(x, y);

	      drawCircle(ctx);

	      ctx.beginPath();
	      ctx.arc(40, -25, 7.5, 0, Math.PI*2);
	      ctx.rect(32, -15, 16, 3);
	      ctx.moveTo(32, -12);
	      ctx.arc(32, -12, 2.5, Math.PI*1, Math.PI*1.5);
	      ctx.moveTo(48, -12);
	      ctx.arc(48, -12, 2.5, Math.PI*1.5, Math.PI*2);
	      ctx.rect(28, -12, 24, 20);
	      ctx.rect(32, 8, 16, 20);
	      ctx.fill();
	      ctx.closePath();

	      ctx.restore();

	      return m.width;
    };



    this.drawManual = function(ctx, x, y) {
	      var m = this.measure(ctx);
	      ctx.save();
	      ctx.translate(x, y);

	      drawCircle(ctx);

	      ctx.beginPath();
	      ctx.moveTo(6, -25);
	      roundedRect(ctx, 20, -25, 30, 40, 5);
	      roundedRect(ctx, 30, -15, 30, 40, 5);
	      ctx.lineWidth = 4;
	      ctx.stroke();
	      ctx.closePath();

	      ctx.restore();

	      return m.width;
    };


    this.measureStamp = function(ctx, label) {
	      ctx.font = '60px sans-serif';
	      var tm = ctx.measureText(label);
	      return {width: tm.width + 40 + 8, align: right};
    };

    this.drawStamp = function(ctx, label, x, y, stamplinewidth) {

        stamplinewidth = stamplinewidth || 8;

	      ctx.save();
	      ctx.translate(x, y);

	      ctx.font = '60px sans-serif';
	      var tm = ctx.measureText(label);

	      ctx.beginPath();
	      var m = this.measure(ctx, label);
	      ctx.rect(stamplinewidth/2, -40, m.width - stamplinewidth, 80+(stamplinewidth/2), Math.PI*2);
	      ctx.lineWidth = stamplinewidth;
	      ctx.stroke();
	      ctx.closePath();

	      ctx.fillText(label, (m.width - stamplinewidth - tm.width)/2, 20);

	      ctx.restore();
	      return m.width;
    };


    this.drawQRcode = function(ctx, size, url) {
        var code;
        // code = new QRCode(-1, QRErrorCorrectLevel.L);
        //  code = new qrcode(1, 'L');
	      code = new qrcode(4, 'L');
	      code.addData(url);
	      code.make();
        
	      ctx.save();
	      var scale = size / (code.getModuleCount()+2);
	      ctx.scale(scale, scale);

	      // draw on the canvas
	      ctx.beginPath();
	      for (var row = 0; row < code.getModuleCount(); row++){
	          for (var col=0; col < code.getModuleCount(); col++){
		            if (code.isDark(row, col)) {
		                ctx.rect(col+1, row+1, 1, 1);
		            }
	          }
	      }
	      ctx.closePath();
	      ctx.fill();
	      ctx.restore();
    };

    this.init(elementID, w, h);
};
